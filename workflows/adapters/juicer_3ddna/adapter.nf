// Juicer + 3D-DNA 适配器（冻结流程 #001 步 3~4）
// 通道契约定义。真实执行依赖服务器上安装的 Juicer / 3D-DNA，由用户经 SOP 包触发。
// 人工调图（Juicebox）是本路线的硬性人类闸口，不可被任何 process 替代。

// ---- 输入通道 ----
input tuple:
    path(hifi_draft)   // draft contigs FASTA（步 2 产物）
    path(hic_r1)       // Hi-C R1 fastq
    path(hic_r2)       // Hi-C R2 fastq
    val(reference)     // 基因组参考（供 juicer）
    val(id)            // 样本/任务标识

// ---- Juicer：Hi-C 比对 -> .hic 与 merged_nodups ----
process JUICER:
    output:
        path "*.hic"        // 互作矩阵
        path "*merged_nodups.bam"
    script:
    // 依赖：juicer.sh；参照 technology_registry；Bam 不得被误判为组装源

// ---- 3D-DNA：脚手架 ----
process THREE_D_DNA:
    input:
        path(hic)
        path(draft)
    output:
        path "*.p_ctg.gfa"    // 脚手架图（历史产物命名一致）
        path "*.lowQ.bed"
    script:
    // 依赖：run-asm-pipeline.sh；产 pacemaker 解码的 gfa

// ---- 人工审查洞门（HUMAN GATE）----
// soil: 3D-DNA 输出必须交由人类经 Juicebox 调图并批准后，方可进入单倍型分离。
// 一旦此门未获 approved，下游不得触发。参照 state_registry 的 WAITING_REVIEW 流转。