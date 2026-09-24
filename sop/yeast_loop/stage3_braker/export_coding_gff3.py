#!/usr/bin/env python3
"""Export a CDS-connected GFF3 subset and verify both FASTA sets unchanged."""

import argparse
from collections import Counter
from dataclasses import dataclass, replace
import faulthandler
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import unquote


TRANSCRIPTS = {"mRNA", "transcript"}
LEAVES = {"exon", "CDS", "intron", "start_codon", "stop_codon"}
PREFIX = "Siganus.intron08.longest"


@dataclass
class Feature:
    fields: list
    attributes: dict

    @property
    def kind(self):
        return self.fields[2]

    @property
    def identifier(self):
        return unquote(self.attributes.get("ID", ""))

    @property
    def parents(self):
        return {unquote(p) for p in self.attributes.get("Parent", "").split(",") if p}

    def text(self):
        attributes = ";".join(f"{key}={value}" for key, value in self.attributes.items())
        return "\t".join(self.fields[:8] + [attributes or "."]) + "\n"


def read_gff(path, regions=None):
    """Yield one feature at a time; do not retain exon/CDS rows in memory."""
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.startswith("##FASTA"):
                break
            if regions is not None and line.startswith("##sequence-region"):
                regions.append(line.rstrip())
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"{path}:{line_number}: expected nine GFF3 fields")
            attributes = {}
            for item in fields[8].split(";"):
                if item in {"", "."}:
                    continue
                key, separator, value = item.partition("=")
                if not separator or key in attributes:
                    raise ValueError(f"{path}:{line_number}: invalid/repeated attribute")
                attributes[key] = value
            yield Feature(fields, attributes)


@dataclass
class CodingPlan:
    genes: set
    transcripts: set
    report: dict


def index_coding(features):
    genes, transcripts = set(), {}
    coding, leaf_parents, exon_parents = set(), set(), set()
    counts = Counter()
    for feature in features:
        counts[feature.kind] += 1
        if feature.kind not in {"gene"} | TRANSCRIPTS | LEAVES:
            raise ValueError(f"Unexpected feature type: {feature.kind}; inspect before filtering")
        if feature.kind == "gene" or feature.kind in TRANSCRIPTS:
            identifier = feature.identifier
            if not identifier or identifier in genes or identifier in transcripts:
                raise ValueError(f"Missing or repeated gene/transcript ID: {identifier}")
            if feature.kind == "gene":
                if feature.parents:
                    raise ValueError(f"Unexpected parent above gene {identifier}")
                genes.add(identifier)
            else:
                transcripts[identifier] = feature.parents
        if feature.kind in LEAVES:
            if not feature.parents:
                raise ValueError(f"Missing parent on {feature.kind}")
            leaf_parents.update(feature.parents)
            if feature.kind == "CDS":
                coding.update(feature.parents)
            elif feature.kind == "exon":
                exon_parents.update(feature.parents)
    for identifier, parents in transcripts.items():
        if len(parents) != 1 or not parents <= genes:
            raise ValueError(f"Transcript needs one existing gene parent: {identifier}")
    if not leaf_parents <= transcripts.keys():
        raise ValueError("Unresolved/non-transcript parent on a leaf feature")
    if not coding:
        raise ValueError("No CDS-connected transcripts found")
    gene_counts = Counter(parent for tid in coding for parent in transcripts[tid])
    if any(count != 1 for count in gene_counts.values()):
        raise ValueError("Multiple coding transcripts per gene remain; do not label this a longest set")
    kept_genes = set(gene_counts)

    without_cds = set(transcripts) - coding
    report = {
        "source_features": dict(counts),
        "coding_transcripts": len(coding),
        "coding_gene_ids": len(kept_genes),
        "excluded_gene_ids": sorted(set(genes) - kept_genes),
        "excluded_transcript_ids_without_CDS": sorted(without_cds),
        "excluded_transcripts_with_exons": len(exon_parents & without_cds),
    }
    return CodingPlan(kept_genes, coding, report)


def filter_features(features, plan):
    for feature in features:
        if feature.kind == "gene":
            keep = feature.identifier in plan.genes
        elif feature.kind in TRANSCRIPTS:
            keep = feature.identifier in plan.transcripts
        else:
            keep = bool(feature.parents & plan.transcripts)
            if keep and not feature.parents <= plan.transcripts:
                # Trim only shared Parent references; coordinates and IDs stay intact.
                attributes = dict(feature.attributes)
                attributes["Parent"] = ",".join(
                    p for p in attributes["Parent"].split(",") if unquote(p) in plan.transcripts
                )
                feature = replace(feature, attributes=attributes)
        if keep:
            yield feature


def fasta_fingerprints(path):
    records = {}
    identifier, length, digest = None, 0, None

    def finish():
        if identifier is None:
            return
        if not length or identifier in records:
            raise ValueError(f"Empty sequence or repeated ID in {path}: {identifier}")
        records[identifier] = (length, digest.hexdigest())

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                finish()
                header = line[1:].split()
                if not header:
                    raise ValueError(f"Empty FASTA header: {path}")
                identifier, length, digest = header[0], 0, hashlib.sha256()
            elif line.strip():
                if identifier is None:
                    raise ValueError(f"Sequence before FASTA header: {path}")
                sequence = "".join(line.split()).encode("ascii")
                length += len(sequence)
                digest.update(sequence)
    finish()
    if not records:
        raise ValueError(f"Empty FASTA: {path}")
    return records


def require_same_fasta(before, after, label):
    if before != after:
        missing, added = before.keys() - after.keys(), after.keys() - before.keys()
        changed = {k for k in before.keys() & after.keys() if before[k] != after[k]}
        raise ValueError(f"{label} changed: missing={len(missing)}, added={len(added)}, sequence={len(changed)}")


def run(candidate, genome, gffread, prefix=PREFIX):
    print("export_coding_gff3: streaming-v2", flush=True)
    candidate = candidate.resolve()
    genome = genome.resolve()
    if not prefix or Path(prefix).name != prefix or "/" in prefix or "\\" in prefix:
        raise ValueError("Prefix must be a filename, not a path")
    source = candidate / prefix
    output = candidate / "coding_only_verified"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    if not genome.is_file():
        raise FileNotFoundError(genome)
    source_gff = Path(str(source) + ".gff3")
    print("[1/6] Indexing GFF3 gene/transcript relationships", flush=True)
    regions = []
    plan = index_coding(read_gff(source_gff, regions))
    coding, report = plan.transcripts, plan.report
    print(f"Indexed {sum(report['source_features'].values())} feature rows", flush=True)
    print("[2/6] Fingerprinting source protein and CDS FASTA", flush=True)
    original = {suffix: fasta_fingerprints(Path(str(source) + suffix))
                for suffix in (".pep.fa", ".cds.fa")}
    for suffix, records in original.items():
        if records.keys() != coding:
            raise ValueError(f"Source {suffix} IDs do not match CDS-connected transcripts")

    stage = Path(tempfile.mkdtemp(prefix=".coding_check_", dir=candidate))
    print(f"Staging directory: {stage}", flush=True)
    stem = stage / prefix
    emitted = Counter()
    print("[3/6] Streaming the CDS-connected subset to disk", flush=True)
    with Path(str(stem) + ".gff3").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("##gff-version 3\n")
        handle.write("# CDS-connected subset; original annotations retained separately.\n")
        for region in regions:
            handle.write(region + "\n")
        for feature in filter_features(read_gff(source_gff), plan):
            handle.write(feature.text())
            emitted[feature.kind] += 1
    report["exported_features"] = dict(emitted)
    print("[4/6] Validating exported GFF3 relationships", flush=True)
    checked = index_coding(read_gff(Path(str(stem) + ".gff3")))
    if (checked.transcripts != coding or checked.genes != plan.genes
            or checked.report["excluded_transcript_ids_without_CDS"]
            or checked.report["excluded_gene_ids"]
            or checked.report["source_features"] != dict(emitted)):
        raise ValueError("Exported GFF3 failed structure validation")
    del checked

    print(f"[5/6] Running gffread; log: {stage / 'gffread.log'}", flush=True)
    with (stage / "gffread.log").open("w", encoding="utf-8") as log:
        try:
            subprocess.run([gffread, str(stem) + ".gff3", "-g", str(genome),
                            "-y", str(stem) + ".pep.fa", "-x", str(stem) + ".cds.fa"],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            reason = (f"signal {-exc.returncode}" if exc.returncode < 0
                      else f"exit code {exc.returncode}")
            raise RuntimeError(f"gffread failed with {reason}; see {stage / 'gffread.log'}") from exc
    print("[6/6] Verifying identical IDs and sequences", flush=True)
    for suffix in original:
        require_same_fasta(original[suffix], fasta_fingerprints(Path(str(stem) + suffix)), suffix)
    report.update({"script_revision": "streaming-v2",
                   "source_gff3": str(source) + ".gff3", "genome": str(genome),
                   "protein_IDs_and_sequences_unchanged": True,
                   "CDS_IDs_and_sequences_unchanged": True,
                   "note": "Exclusion from this coding subset does not establish biological noncoding status."})
    (stage / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}; staging retained at {stage}")
    stage.rename(output)
    print(f"Source gene records: {report['source_features'].get('gene', 0)}")
    print(f"Coding genes: {report['coding_gene_ids']}")
    print(f"Coding transcripts: {report['coding_transcripts']}")
    print(f"Excluded genes without coding transcripts: {len(report['excluded_gene_ids'])}")
    print(f"Excluded transcripts without CDS: {len(report['excluded_transcript_ids_without_CDS'])}")
    print(f"Excluded transcripts with exons: {report['excluded_transcripts_with_exons']}")
    print("Protein IDs and sequences: UNCHANGED")
    print("CDS IDs and sequences: UNCHANGED")
    print(f"VERIFIED OUTPUT: {output}")


if __name__ == "__main__":
    faulthandler.enable()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--genome", type=Path, required=True)
    parser.add_argument("--gffread", default="${SHARED}/env/braker3/bin/gffread")
    parser.add_argument("--prefix", default=PREFIX)
    args = parser.parse_args()
    run(args.candidate, args.genome, args.gffread, args.prefix)
