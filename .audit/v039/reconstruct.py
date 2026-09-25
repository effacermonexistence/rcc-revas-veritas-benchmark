"""Reconstruct the reviewed v0.3.9 from the exact archived v0.3.8 source."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);a=p.parse_args()
r=a.output
shutil.copytree(a.base,r,ignore=shutil.ignore_patterns('.git','__pycache__','.pytest_cache','*.egg-info'))
def edit(rel,old,new):
 f=r/rel;t=f.read_text();assert t.count(old)==1,(rel,old);f.write_text(t.replace(old,new))
code=r/'src/rveval/integrations/rcc_external.py';old_code_hash=hashlib.sha256(code.read_bytes()).hexdigest()
edit('src/rveval/integrations/rcc_external.py','sha_file, sha_json, read_json','sha_file, sha_json, read_json, canonical_bytes')
edit('src/rveval/integrations/rcc_external.py',
"""        if type(candidate.content) is not int or candidate.content not in task['classes']:
            return {'status':'REJECT','scope':'PUBLIC_CLASS_MEMBERSHIP','evidence_refs':refs}""",
"""        classes = task['classes']
        require(type(classes) is list, 'PUBLIC_CLASS_SET_MUST_BE_LIST')
        # Class labels belong to the benchmark, not to Python's integer type.
        # Use the declared typed JSON profile: true, 1, 1.0 and -0.0 are distinct.
        # Empty classes explicitly admit no label. Malformed class contracts are
        # integration errors, not fabricated governance or task verdicts.
        encoded = canonical_bytes(candidate.content)
        if not any(encoded == canonical_bytes(label) for label in classes):
            return {'status':'REJECT','scope':'PUBLIC_CLASS_MEMBERSHIP','evidence_refs':refs}""")
new_code_hash=hashlib.sha256(code.read_bytes()).hexdigest()
policies=[r/'policies/external-output-contract.v0.3.json',r/'src/rveval/resources/policy.json']
old_policy_hashes=set()
for f in policies:
 old_policy_hashes.add(hashlib.sha256(f.read_bytes()).hexdigest())
 t=f.read_text();assert old_code_hash in t
 f.write_text(t.replace(old_code_hash,new_code_hash).replace('"version": "0.3.0"','"version": "0.3.9"'))
new_policy_hash=hashlib.sha256(policies[0].read_bytes()).hexdigest()
assert policies[0].read_bytes()==policies[1].read_bytes()
for f in r.rglob('*.json'):
 if f.name=='SOURCE_MANIFEST.json' or f in policies:continue
 t=f.read_text();changed=t
 for old in old_policy_hashes:changed=changed.replace(old,new_policy_hash)
 if changed!=t:f.write_text(changed)
edit('src/rveval/partner_mapping.py',"handoff.get('candidate') == candidate.to_dict()","sha_json(handoff.get('candidate')) == sha_json(candidate.to_dict())")
edit('src/rveval/partner_mapping.py',"handoff.get('verification') == body.get('verification')","sha_json(handoff.get('verification')) == sha_json(body.get('verification'))")
edit('src/rveval/snapshot.py','context[key] == value','sha_json(context[key]) == sha_json(value)')
edit('src/rveval/freeze.py','observed==frozen["state"]','sha_json(observed)==sha_json(frozen["state"])')
edit('src/rveval/evidence.py','wanted==evidence_index(directory)','sha_json(wanted)==sha_json(evidence_index(directory))')
for rel in ['pyproject.toml','src/rveval/__init__.py']:edit(rel,'0.3.8','0.3.9')
notes='''
## Typed public class contracts and exact identity in 0.3.9

The optional public `task.classes` constraint is an array of finite JSON labels,
not a list of correct answers. Labels may be strings (including Unicode), booleans,
null, numbers or structured JSON values. Class membership compares canonical bytes
under `rveval.python-finite-json.v2`. Accordingly `true`, `1`, `1.0`, `0.0` and
`-0.0` are distinct representations. Use an explicit, separately pinned adapter
normalization when a benchmark intentionally equates representations; do not
rely on Python's implicit numeric equality. Empty classes admit no label.
Malformed non-array class contracts raise `PUBLIC_CLASS_SET_MUST_BE_LIST` as an
integration error, not a candidate refusal. No class constraint means no implicit
classification restriction. This remains output-contract validation, not factual
accuracy, gold-label access or execution authority.

The same typed identity is required for a declared existing candidate/context
binding, the known RCC handoff candidate and verification reports, frozen plugin
identity, and the full evidence index. Rehashing an outer packet does not make a
boolean/number substitution equal to the retained inner record. Protocol shapes
and native upstream source pins are unchanged. Old result snapshots retain their
original meaning; use a new freeze for the updated policy/source pins.
'''
for rel in ['docs/PARTNER_START_HERE.md','src/rveval/resources/PARTNER_START_HERE.md']:
 edit(rel,'# Partner implementation guide — 0.3.8','# Partner implementation guide — 0.3.9')
 f=r/rel;f.write_text(f.read_text()+notes)
(r/'CHANGELOG_v0.3.9.md').write_text('''# Version 0.3.9: typed identity review

Input: remote commit `85224ecfd965f7aff6c3d5d8a772f49c17db717c`,
source tree `e21e28aab4cd879e13a3422daf152841c51320e6`.

One root defect family was reproduced: Python equality and integer-only
classification were inconsistent with the typed canonical JSON contract.
Positive categorical-label probes and numeric/boolean alias probes failed in
the unchanged previous release. This revision uses the existing typed profile
for public class membership, existing context bindings, known RCC handoff
records, frozen state and evidence-index identity. It does not introduce an
authenticity claim, change an official scorer, synthesize permissions or replace
a native benchmark with a fixture.

The public output policy is explicitly versioned 0.3.9 and its source/content
pins are updated in active examples and the installed pilot template.
'''+notes)
f=r/'README.md';f.write_text('Current review: **0.3.9**. See `CHANGELOG_v0.3.9.md`.\n\n'+f.read_text())
(r/'PUBLICATION_SOURCE.json').write_text(json.dumps({'version':'0.3.9','base_repository_commit':'85224ecfd965f7aff6c3d5d8a772f49c17db717c','base_source_tree':'e21e28aab4cd879e13a3422daf152841c51320e6','scope':'ADDITIVE_TYPED_IDENTITY_REVIEW','historical_versions_modified':False},indent=2)+'\n')
for name in ['test_typed_public_classes.py','test_typed_boundary_identity.py']:shutil.copyfile(a.assets/name,r/'tests'/name)
subprocess.run(['python',str(r/'scripts/source_manifest.py')],check=True)
subprocess.run(['python',str(r/'scripts/verify_source_manifest.py')],check=True)
