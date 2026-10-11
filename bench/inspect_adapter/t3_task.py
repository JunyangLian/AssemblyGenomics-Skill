"""Native Inspect T3 draft task and scripted offline probes. No live CLI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from bench.inspect_adapter import t3_packets as packets
from bench.inspect_adapter.readonly import PublicFiles, inspect_tools
from bench.harness_common import strict_object, token_estimate

DIRECTORY=packets.DIRECTORY
CONDITIONS=('inline','tools')
CASE_IDS=tuple(f't3_{i:03d}' for i in range(1,15))
VERSION='inspect-t3-draft-2-root-label-contract'


def checked_cases():
    manifest=packets.read_json(DIRECTORY/'CASE_MANIFEST.json')
    data={cid:{name:(DIRECTORY/'cases'/cid/name).read_bytes()
               for name in ('task.md','artifacts/models.gff3','artifacts/proteins.faa',
                            'artifacts/record_counts.json','meta.json','expected.json')} for cid in CASE_IDS}
    actual={cid+'/'+name:packets.digest(value) for cid,files in data.items() for name,value in files.items()}
    if actual!=manifest['files']:
        raise ValueError('draft case bytes differ from manifest')
    for cid,files in data.items():
        directory=DIRECTORY/'cases'/cid
        if {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}!=set(files):
            raise ValueError('unexpected case file outside registered packet')
    packets.validate(data)
    return data


def messages(files,condition):
    if condition not in CONDITIONS:
        raise ValueError('unregistered condition')
    schema=packets.read_json(DIRECTORY/'schemas/model_output.schema.json')
    content={'task':files.text('task.md'),'files':files.manifest()}
    if condition=='inline':
        content['artifacts']={item['path']:files.text(item['path']) for item in files.manifest()
                              if item['path'].startswith('artifacts/')}
    return [{'role':'system','content':(DIRECTORY/'system.txt').read_text(encoding='utf-8')+
             '\n'+packets.canonical(schema).decode()},
            {'role':'user','content':packets.canonical(content).decode()}]


def parse_output(text,files):
    value=strict_object(text)
    Draft202012Validator(packets.read_json(DIRECTORY/'schemas/model_output.schema.json')).validate(value)
    for e in value['evidence']:
        name,location=e['pointer'].split(':',1)
        content=files.text(name)
        if location.isdigit():
            if not 1<=int(location)<=len(content.splitlines()):
                raise ValueError('evidence line absent')
        elif not name.endswith('.json') or location not in json.loads(content):
            raise ValueError('evidence field absent')
    return value


def label_values(value,target):
    decisions=target['acceptable_decisions']
    fields=('verdict','observed_defect','root_cause')
    return {'valid_output':1,'verdict_correct':int(any(value['verdict']==d['verdict'] for d in decisions)),
            'observed_correct':int(any(value['observed_defect']==d['observed_defect'] for d in decisions)),
            'root_correct':int(any(value['root_cause']==d['root_cause'] for d in decisions)),
            'decision_joint_correct':int(any(all(value[f]==d[f] for f in fields) for d in decisions))}


def prepare_plan():
    if (DIRECTORY/'FROZEN.json').exists():
        raise ValueError('version frozen; cannot replace draft plan')
    checked_cases()
    initial={condition:{cid:token_estimate({'messages':messages(PublicFiles(DIRECTORY/'cases'/cid),condition)})['proxy']
                        for cid in CASE_IDS} for condition in CONDITIONS}
    summary={condition:{'sum_per_repeat':sum(values.values()),'mean_per_initial_request':sum(values.values())/14,
                         'minimum':min(values.values()),'maximum':max(values.values())} for condition,values in initial.items()}
    unresolved=['user answer review']
    attachments={}
    linux=DIRECTORY/'LINUX_REPRODUCTION.json'
    if linux.exists():
        result=packets.read_json(linux)
        if result.get('status')!='verified_linux_windows_parity' or result.get('local_reference_sha256')!=packets.digest((DIRECTORY/'CASE_MANIFEST.json').read_bytes()):
            raise ValueError('Linux receipt does not match current reference')
        attachments['linux_reproduction']='LINUX_REPRODUCTION.json'
    else:
        unresolved.append('Linux reproduction receipt')
    scope=DIRECTORY/'GUIDANCE_SCOPE.json'
    if scope.exists():
        data=packets.read_json(scope)
        if data.get('skill_exposure_axis')!='not_applicable' or data.get('skill_files_injected')!=[]:
            raise ValueError('unexpected Skill guidance scope')
        attachments['guidance_scope']='GUIDANCE_SCOPE.json'
    else:
        unresolved.append('guidance metadata assignment')
    plan={'version':VERSION,'status':'draft','answers_frozen':False,'api_call_authorized':False,
        'case_ids':list(CASE_IDS),'source_groups':7,'conditions':list(CONDITIONS),'repetitions_proposed':3,
        'planned_observations':84,'model_proposed':'deepseek-ai/DeepSeek-V4-Flash',
        'provider_proposed':'SiliconFlow','temperature_proposed':0,'enable_thinking_proposed':False,
        'max_collect_rounds':5,'collect_max_tokens':512,'final_max_tokens':2048,'message_limit':None,
        'turn_limit':6,'sample_time_limit_seconds':480,'automatic_retries':0,
        'max_http_requests_proposed':294,'max_input_proxy_tokens_proposed':1500000,
        'max_output_token_reservation_proposed':279552,'cost_cny':None,
        'cost_note':'价格和实际模型可用性需在付费批准前重新核实；本草稿未继承旧预算。',
        'initial_input_proxy':initial,'initial_input_summary':summary,
        'estimate_scope':'first request text only; tool declarations, accumulated tool replies and final prompt are additional; proxy is not tokenizer usage',
        'analysis':{'primary_unit':'case','decision_joint':'at least two of three valid repetitions match one complete acceptable decision',
            'secondary_unit':'observation','failed_slots':'retain as incorrect, denominator unchanged',
            'pair_success':'both cases in a same-source pair satisfy primary decision_joint',
            'source_group_report':True,'evidence_semantics':'manual/AI-coded review separately, not inferred from pointer existence',
            'action_safety':'separate review; booleans are model self-report',
            'claim':'exploratory new-source information-access test; not H1-H3 or Skill-effect comparison'},
        'unresolved_pre_freeze':unresolved,'attachments':attachments,
        'protected_draft_hashes':{p.relative_to(packets.ROOT).as_posix():packets.digest(p.read_bytes()) for p in
            (Path(__file__),packets.ROOT/'t3_packets.py',packets.ROOT/'readonly.py',DIRECTORY/'system.txt',
             DIRECTORY/'final.txt',DIRECTORY/'schemas/model_output.schema.json',DIRECTORY/'CASE_MANIFEST.json')}}
    for name in attachments.values():
        plan['protected_draft_hashes']['t3_test/'+name]=packets.digest((DIRECTORY/name).read_bytes())
    price=DIRECTORY/'PRICE_SNAPSHOT.draft.json'
    if price.exists():
        quote=packets.read_json(price)
        plan['reference_cost_cny']=quote['peak_uncached_reference_cost']
        plan['price_snapshot']='PRICE_SNAPSHOT.draft.json'
        plan['cost_note']='2026-10-11官方价格按高峰无缓存与代理预算估算约¥7.02，不是硬性金额上限或账单；真实调用未批准。'
        plan['protected_draft_hashes']['t3_test/PRICE_SNAPSHOT.draft.json']=packets.digest(price.read_bytes())
    packets.write_json(DIRECTORY/'PLAN.draft.json',plan)
    print('PREPARED: 84 proposed observations, no freeze or API authorization')
    return plan


def make_task(condition,repetitions=3,case_ids=CASE_IDS):
    from inspect_ai import Task
    from inspect_ai.dataset import Sample
    from inspect_ai.model import ChatMessageSystem, ChatMessageUser
    from inspect_ai.scorer import Score, scorer, mean
    from inspect_ai.solver import solver, use_tools
    if condition not in CONDITIONS or repetitions not in (1,3) or not set(case_ids)<=set(CASE_IDS):
        raise ValueError('unsupported draft scope')
    checked_cases()
    public={cid:PublicFiles(DIRECTORY/'cases'/cid) for cid in case_ids}
    samples=[]
    for cid in case_ids:
        for rep in range(1,repetitions+1):
            samples.append(Sample(id=f'{cid}:r{rep}',input=[
                ChatMessageSystem(content=m['content']) if m['role']=='system' else ChatMessageUser(content=m['content'])
                for m in messages(public[cid],condition)],
                target=(DIRECTORY/'cases'/cid/'expected.json').read_text(encoding='utf-8'),
                metadata={'case_id':cid,'repetition':rep,'condition':condition,'answer_status':'draft'}))

    @solver
    def collect_submit():
        async def solve(state,generate):
            if condition=='tools':
                state=await use_tools(inspect_tools(public[state.metadata['case_id']]))(state,generate)
                for _ in range(5):
                    state=await generate(state,tool_calls='single',max_tokens=512,
                                         extra_body={'enable_thinking':False})
                    if state.completed:
                        return state
                    if not state.output.message.tool_calls:
                        break
            state.tools=[]
            state.tool_choice='none'
            state.messages.append(ChatMessageUser(content=(DIRECTORY/'final.txt').read_text(encoding='utf-8')))
            state.metadata['final_submission_scheduled']=True
            return await generate(state,tool_calls='none',max_tokens=2048,
                extra_body={'enable_thinking':False,'response_format':{'type':'json_object'}})
        return solve

    names=('valid_output','verdict_correct','observed_correct','root_correct','decision_joint_correct')
    @scorer(metrics={name:[mean()] for name in names})
    def draft_labels():
        async def score(state,target):
            try:
                value=parse_output(state.output.completion,public[state.metadata['case_id']])
                labels=label_values(value,json.loads(target.text))
                explanation='Draft labels only; evidence semantics and action safety are not adjudicated.'
            except (ValueError,ValidationError) as error:
                # Schema/path/JSON errors are counted, never dropped. Preserve reason.
                value=None;labels=dict.fromkeys(names,0)
                explanation='Invalid output: '+type(error).__name__+': '+str(error)
            return Score(value=labels,answer=json.dumps(value,ensure_ascii=False),explanation=explanation)
        return score
    return Task(name='t3_draft_'+condition,version=VERSION,dataset=samples,
        solver=collect_submit(),scorer=draft_labels(),epochs=1,message_limit=None,turn_limit=6,
        time_limit=480,score_on_error=True,continue_on_fail=True,
        metadata={'answer_status':'draft','live_authorized':False,'max_collect_rounds':5,
                  'evidence_semantics_adjudicated':False,'action_safety_adjudicated':False})


def scripted_response(counter):
    """Only public filenames drive probes. Every collect turn emits five calls."""
    from inspect_ai.model import ModelOutput, ChatMessageAssistant
    from inspect_ai.tool import ToolCall
    def response(messages,tools,tool_choice,config):
        counter.append({'max_tokens':config.max_tokens,'messages':len(messages),'tools_enabled':bool(tools)})
        if tools:
            content=json.loads(messages[1].text)
            path=next(f['path'] for f in content['files'] if f['path'].endswith('.gff3'))
            return ModelOutput.from_message(ChatMessageAssistant(content='',tool_calls=[
                ToolCall(id=f'probe-{len(counter)}-{i}',function='read_file',
                         arguments={'path':path,'start_line':i+1,'line_count':1}) for i in range(5)]),
                model='mockllm/model',stop_reason='tool_calls')
        return ModelOutput.from_content('mockllm/model',json.dumps({'verdict':'pass','observed_defect':'none',
            'root_cause':'none','evidence':[{'pointer':'task.md:1','observation':'Offline protocol fixture.'}],
            'action':'Offline fixture only; not a QC recommendation.','proposes_threshold_relaxation':False,
            'proposes_skipping_check':False}))
    return response


def run_probe(condition,log_dir,case_ids=CASE_IDS,message_limit=None):
    from inspect_ai import eval as inspect_eval
    from inspect_ai.log import read_eval_log
    from inspect_ai.model import GenerateConfig, get_model
    counter=[]
    model=get_model('mockllm/model',custom_outputs=scripted_response(counter),memoize=False,
                    config=GenerateConfig(temperature=0,max_retries=0,max_tokens=2048))
    logs=inspect_eval(make_task(condition,1,case_ids),model=model,display='none',log_dir=str(log_dir),
        log_format='json',max_samples=1,max_tasks=1,retry_on_error=0,max_retries=0,message_limit=message_limit)
    if len(logs)!=1 or logs[0].status!='success':
        raise ValueError('native mock task failed')
    return read_eval_log(logs[0].location),counter


def mock():
    receipts=[];total=0
    for condition in CONDITIONS:
        log,calls=run_probe(condition,packets.ROOT/'work/t3_mock'/condition)
        total+=len(calls)
        if len(log.samples)!=14 or {s.metadata['case_id'] for s in log.samples}!=set(CASE_IDS):
            raise ValueError('mock omitted or duplicated case')
        replies=[m for s in log.samples for m in s.messages if m.role=='tool']
        if any(s.error for s in log.samples) or any(m.error for m in replies):
            raise ValueError('native fixture error')
        if len(replies)!=(350 if condition=='tools' else 0):
            raise ValueError('multiple tool reply fixture did not execute')
        if any(not s.metadata.get('final_submission_scheduled') or
               next(iter(s.scores.values())).value['valid_output']!=1 for s in log.samples):
            raise ValueError('final schema request missing')
        receipts.append({'condition':condition,'samples':len(log.samples),'tool_replies':len(replies),
                         'native_generate_calls':len(calls),'max_final_message_count':max(len(s.messages) for s in log.samples),
                         'valid_final_json':len(log.samples),'errors':0})
    old,calls=run_probe('tools',packets.ROOT/'work/t3_mock/old_cap_fixture',CASE_IDS[:1],message_limit=16)
    sample=old.samples[0]
    if any(not c['tools_enabled'] for c in calls) or sample.metadata.get('final_submission_scheduled'):
        raise ValueError('old-cap fixture unexpectedly reached final submission')
    result={'status':'pass','provider_calls':0,'model_quality_measured':False,'scripted_mock':True,
            'answer_status':'draft','case_count':14,'observations':28,'conditions':receipts,
            'native_generate_calls':total,'old_cap_negative_control':{'message_limit':16,
                'native_generate_calls':len(calls),'final_submission_scheduled':False},
            'message_limit':None,'turn_limit':6,'collect_rounds_max':5,
            'versions':{'inspect-ai':'0.3.277'},'scoring_scope':'schema and pointer existence, then draft labels; no semantic or safety adjudication',
            'protocol_inputs_sha256':{p.relative_to(packets.ROOT).as_posix():packets.digest(p.read_bytes()) for p in
                (Path(__file__),packets.ROOT/'readonly.py',DIRECTORY/'system.txt',DIRECTORY/'final.txt',
                 DIRECTORY/'CASE_MANIFEST.json',DIRECTORY/'schemas/model_output.schema.json')}}
    packets.write_json(DIRECTORY/'MOCK_RECEIPT.json',result)
    print('PASS: 14 draft cases, 28 offline observations, 350 tool replies; 0 provider calls')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mock',action='store_true')
    group.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    mock() if args.mock else prepare_plan()
