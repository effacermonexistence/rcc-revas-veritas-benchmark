#!/usr/bin/env python3
"""Author-time schema generator; emitted schemas are committed and hash-pinned."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
STR={'type':'string','minLength':1,'maxLength':10000}
UTC={'type':'string','pattern':r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$'}
SS={'type':'array','items':STR,'uniqueItems':True}
NN={'type':'integer','minimum':0,'maximum':2**53-1}
ANY={'$ref':'#/$defs/value'}
def obj(props,required=None):
 return {'type':'object','properties':props,'required':list(props) if required is None else required,'additionalProperties':False}
def nullable(x): return {'anyOf':[x,{'type':'null'}]}
value={'anyOf':[{'type':'null'},{'type':'boolean'},{'type':'integer','minimum':-(2**53-1),'maximum':2**53-1},{'type':'string'}, {'type':'array','items':{'$ref':'#/$defs/value'}},{'type':'object','additionalProperties':{'$ref':'#/$defs/value'}}]}
binding=obj({**{k:STR for k in ['request_id','object_id','state_id','policy_id','policy_version']},'state_version':NN,'scope':{**SS,'minItems':1}})
action=obj({**{k:nullable(STR) for k in ['actor_identity','action_class','canonical_action','target_system','target_resource']},'requested_scope':nullable({**SS,'minItems':1}),'parameters':nullable({'type':'object','additionalProperties':ANY})})
claim=obj({'value':ANY,'epistemic_type':{'enum':['FACT','INFERENCE','ACTION_PROPOSAL']}})
evidence=obj({'payload':obj({'evidence_id':STR,'issuer':STR,'synthetic':{'type':'boolean'},'binding':binding,'candidate_hash':STR,'issued_at':UTC,'expires_at':UTC,'observations':{'type':'object','additionalProperties':ANY}}),'signature':{'type':'string'}})
input_schema=obj({'schema_version':{'const':'rcc-revas.runtime-input.v1'},'case_id':STR,'synthetic':{'type':'boolean'},
 'request':obj({'kind':{'enum':['factual_claim','bounded_inference','candidate_replacement','protected_action']},'binding':binding,'as_of':UTC,'claims':{**SS,'minItems':1},'typed_action':nullable(action)}),
 'candidate':obj({'candidate_id':STR,'candidate_type':{'enum':['structured_claims','hypothesis','structured_action']},'binding':binding,'claims':{'type':'object','additionalProperties':claim},'content':ANY,'typed_action':nullable(action)}),
 'evidence':{'type':'array','maxItems':1000,'items':evidence},
 'upstream_fallback':nullable(obj({'value':ANY,'epistemic_type':{'enum':['FACT','INFERENCE','UNVERIFIED','ACTION_PROPOSAL']},'source_ref':STR})),
 'lineage':obj({'source_observation_id':nullable(STR),'source_trace_id':nullable(STR),'source_artifact_refs':SS,'measurement_evidence':{'type':'null'}}),
 'handoff_state':nullable(obj({'as_of':UTC,'binding':binding,'revoked_evidence_ids':SS}))})
# Typed optional source-scenario extension; source condition booleans are not
# scoring labels. Evaluation label keys remain recursively forbidden by runtime.
import sys
sys.path.insert(0,str(ROOT))
from rcc_revas_eval.scenario import BOOL_FIELDS, ID_FIELDS, ACTION_FIELDS, ANNOTATION_FIELDS
source_action=obj({k:nullable({**SS,'minItems':1}) if k=='requested_scope' else nullable(STR) for k in sorted(ACTION_FIELDS)},required=[])
governance=obj({**{k:nullable({'type':'boolean'}) for k in sorted(BOOL_FIELDS)},**{k:nullable(STR) for k in sorted(ID_FIELDS)}},required=[])
annotations=obj({k:nullable({'type':'boolean'}) if k=='human_review_required' else nullable(STR) for k in sorted(ANNOTATION_FIELDS)},required=[])
input_schema['properties']['partner_scenario']=obj({'schema_version':{'const':'takeshi.synthetic-scenario.v1'},'synthetic':{'const':True},'source_action':source_action,'governance_fixture':governance,'untrusted_annotations':annotations})
input_schema['$defs']={'value':value}
input_schema['x-runtime-checks']=['exact candidate-content-to-claims binding','kind-to-candidate-type match','candidate and evidence binding','strict calendar-valid UTC timestamps','HMAC issuer scope and freshness','post-adoption recheck','unknown preservation; no upstream expected labels','untyped measurement metadata forbidden','recursive evaluation-only field rejection']
result=obj({'schema_version':{'const':'rcc-revas.runtime-result.v1'},'decision':{'type':'object'},'decision_lock':obj({'status':{'const':'LOCKED'},'version':STR,'hash_algorithm':{'const':'sha256'},'hash_profile':STR,'preimage':STR,'decision_id':STR,'decision_hash':STR,'scoring_labels_accessed':{'const':False},'origin_authentication':STR,'decision_ts':UTC,'time_semantics':STR}), 'handoff_release':{'type':'object'},'handoff_release_hash':STR})
handoff=obj({'artifact_type':{'const':'rcc_revas_to_veritas_handoff'},'artifact_version':{'const':'0.2.0'},'field_contract_version':{'const':'0.2.0'},'source_artifact':{'type':'object'},'lineage':{'type':'object'},'measurement_evidence':{'type':'null'},'rcc_revas':{'type':'object'},'candidate':obj({'selected_output_ref':nullable(STR),'selected_output_hash':nullable(STR),'hash_profile':STR,'candidate_type':nullable(STR),'typed_action':nullable({'type':'object'})}),'adapter_provenance':{'type':'object'},'boundary_assertions':{'type':'object','additionalProperties':{'const':False}},'unresolved_veritas_requirements':SS})
for name,schema in [('runtime_input.schema.json',input_schema),('rcc_result.schema.json',result),('veritas_handoff.schema.json',handoff)]:
 schema['$schema']='https://json-schema.org/draft/2020-12/schema';schema['title']=name
 (ROOT/'schemas'/name).write_text(json.dumps(schema,indent=2,ensure_ascii=False)+'\n')
print('Wrote 3 schemas. Structural equality and digest checks are additionally enforced by runtime code.')
