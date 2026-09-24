"""Create a self-contained, auditable pilot without requiring a source checkout."""
from __future__ import annotations
from importlib.resources import files
from pathlib import Path
import json
from .guardrails import require
from .canonical import write_json_new, sha_file
from .partner_mapping import validate_mapping_contract


def initialize_pilot(output: Path, name: str) -> dict:
    """Create only a new directory. The initial run is an engineering control.

    Native execution, policy provenance and the official scorer must be supplied
    for a real treatment claim. This helper never manufactures those objects.
    """
    require(type(name) is str and bool(name.strip()) and len(name) <= 160,
            'PILOT_NAME_INVALID')
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), 'PILOT_OUTPUT_EXISTS')
    output.mkdir(parents=True, exist_ok=False)
    resource = files('rveval.resources')
    for folder in ('contracts', 'schemas', 'docs'):
        (output / folder).mkdir()
    for entry in resource.iterdir():
        if entry.name.startswith('schema__'):
            (output / 'schemas' / entry.name.removeprefix('schema__')).write_bytes(entry.read_bytes())
        elif entry.name.endswith('.md'):
            (output / 'docs' / entry.name).write_bytes(entry.read_bytes())
    for source, target in [('mapping.json', 'contracts/mapping.json'),
                           ('policy.json', 'policy.json'),
                           ('pilot_worker.py.txt', 'worker.py'),
                           ('pilot_impl.py.txt', 'pilot_impl.py'),
                           ('pilot_start.md', 'START_HERE.md'),
                           ('pilot_start.ja.md', 'START_HERE.ja.md')]:
        (output / target).write_bytes(resource.joinpath(source).read_bytes())
    # Runtime tasks and evaluation-only answers have independently declared files.
    write_json_new(output / 'cases.json', [
        {'case_id': 'sum/one', 'request': 'Sum the supplied numbers.', 'input': {'values': [1, 2, 3]}},
        {'case_id': 'sum/two', 'request': 'Sum the supplied numbers.', 'input': {'values': [-3, 8]}}
    ])
    write_json_new(output / 'targets.json', {'sum/one': 6, 'sum/two': 5})
    argv = ['{python}', 'worker.py', '--request', '{request}', '--output', '{output}']
    config = {'execution_backend': 'native-job/v1', 'study_kind': 'ENGINEERING',
              'case_ids': ['sum/one', 'sum/two'], 'arms': ['A', 'B'],
              'execute_argv': argv, 'score_argv': argv,
              'source_files': ['worker.py', 'pilot_impl.py', 'policy.json'],
              'mapping_contract': 'contracts/mapping.json',
              'runtime_inputs': ['cases.json'], 'scorer_inputs': ['targets.json'],
              'runtime_parameters': {'pilot_name': name,
                 'comparison_role': 'IDENTICAL_ENGINEERING_CONTROL_NOT_VERITAS_TREATMENT'},
              'scorer_parameters': {}, 'timeout_seconds': 300,
              'benchmark_fitness': {'status': 'REVIEWED_APPROPRIATE',
                  'purpose': 'INSTALLATION_ONLY', 'benchmark_revision': 'pilot-transport-example/v1',
                  'reviewed_at': '2026-09-24', 'reason': 'Local transport and handoff check; not capability evidence.',
                  'sources': ['START_HERE.md']}}
    write_json_new(output / 'config.json', config)
    check = validate_mapping_contract(output / 'contracts/mapping.json')
    require(check['status'] == 'PASS', 'PILOT_MAPPING_INVALID')
    from . import __version__
    result = {'status': 'PASS', 'framework_version': __version__, 'pilot': str(output),
              'config': str(output / 'config.json'), 'mapping': check,
              'native_treatment_claim': False,
              'scope': 'GENERATED_ENGINEERING_STARTER_NOT_COMPLETED_EXTERNAL_PILOT',
              'next_command': 'python worker.py is protocol-only; follow START_HERE.md for freeze/run/verify'}
    write_json_new(output / 'pilot-files.json', {'files': [
        {'path': p.relative_to(output).as_posix(), 'sha256': sha_file(p)}
        for p in sorted(output.rglob('*')) if p.is_file()]})
    return result
