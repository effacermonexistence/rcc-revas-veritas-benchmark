"""Read-only verification of the corrected artifact fetched from GitHub."""
from __future__ import annotations
import argparse, gzip, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile, venv, zipfile
from pathlib import Path

COMMIT = '805cd5ff17e431cf50a3dafa7f78a60a704613b9'
DIGEST = '4c736357ab93a8f4b5027b94c20340b973c760de1a0027df30bb53d3d10f47d8'
SOURCE_TREE = 'ab477cff7924b922b0885fb665e5ca0d6e42868a'
PACKAGE_PATH = 'rcc-revas-eval/v0.1.0'
ARCHIVE = 'rcc-revas-eval-v0.1.0-source.tar.gz'

def require(value, code):
    if not value:
        raise RuntimeError(code)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def check_archive(data):
    require(len(data) == 109796 and sha(data) == DIGEST, 'ARCHIVE_IDENTITY_MISMATCH')
    gzip.decompress(data)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    checkout, out = args.checkout.resolve(), args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'FAIL', 'checks': [], 'publication_commit': COMMIT,
              'native_VERITAS_executed': False, 'joint_contract_frozen': False,
              'verification_owner': 'PUBLISHER', 'python': sys.version}
    def command(name, argv, cwd):
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=300)
        (out / (name + '.stdout.txt')).write_text(result.stdout)
        (out / (name + '.stderr.txt')).write_text(result.stderr)
        report['checks'].append({'name': name, 'exit_code': result.returncode})
        require(result.returncode == 0, 'COMMAND_FAILED:' + name)
        return result.stdout.strip()
    try:
        require(command('checkout-pin', ['git', 'rev-parse', 'HEAD'], checkout) == COMMIT, 'WRONG_CHECKOUT')
        package = checkout / PACKAGE_PATH
        pin = json.loads((package / 'CANONICAL_PIN.json').read_text())
        require(pin['source_archive_sha256'] == DIGEST, 'PIN_DIGEST_MISMATCH')
        require(pin['source_archive_size_bytes'] == 109796, 'PIN_SIZE_MISMATCH')
        require(pin['source_git_tree'] == SOURCE_TREE, 'PIN_SOURCE_TREE_MISMATCH')
        require(pin['verified_entrypoint'] == 'python -m rcc_revas_eval evaluate', 'ENTRYPOINT_METADATA_MISMATCH')
        require(pin['joint_contract_frozen'] is False and pin['native_veritas_joint_run_completed'] is False, 'CLAIM_UPGRADE')
        require((package / 'SHA256SUMS.txt').read_text() == DIGEST + '  source/' + ARCHIVE + '\n', 'CHECKSUM_FILE_MISMATCH')
        data = (package / 'source' / ARCHIVE).read_bytes()
        check_archive(data)
        # Negative controls: a truncated or modified payload must never reach execution.
        rejected = 0
        for invalid in (data[:-1], bytes([data[0] ^ 1]) + data[1:], data + b'x'):
            try:
                check_archive(invalid)
            except RuntimeError:
                rejected += 1
        require(rejected == 3, 'ARCHIVE_GATE_NEGATIVE_CONTROL_FAILED')
        report.update(archive_sha256=sha(data), archive_bytes=len(data), archive_negative_controls_rejected=rejected)
        (out / ARCHIVE).write_bytes(data)
        source = out / 'source'
        source.mkdir()
        members = {}
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tf:
            for member in tf.getmembers():
                p = Path(member.name)
                require(not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts, 'UNSAFE_ARCHIVE_PATH')
                if member.isdir():
                    (source / p).mkdir(parents=True, exist_ok=True)
                else:
                    require(member.isfile() and member.name not in members, 'INVALID_OR_DUPLICATE_ARCHIVE_MEMBER')
                    value = tf.extractfile(member).read()
                    (source / p).parent.mkdir(parents=True, exist_ok=True)
                    (source / p).write_bytes(value)
                    (source / p).chmod(0o755 if member.mode & 0o111 else 0o644)
                    members[member.name] = sha(value)
        require(len(members) == 67, 'SOURCE_FILE_COUNT_MISMATCH')
        require(json.loads((package / 'SOURCE_FILES.sha256.json').read_text()) == members, 'PER_FILE_MANIFEST_MISMATCH')
        require(all((package / 'runtime' / p).read_bytes() == (source / p).read_bytes() for p in members), 'ARCHIVE_EXPANDED_BYTE_MISMATCH')
        require(command('published-source-tree', ['git', 'rev-parse', 'HEAD:' + PACKAGE_PATH + '/runtime'], checkout) == SOURCE_TREE, 'PUBLISHED_GIT_TREE_MISMATCH')
        command('extracted-git-init', ['git', 'init', '-q'], source)
        command('extracted-git-index', ['git', '-c', 'core.autocrlf=false', 'add', '-f', '.'], source)
        require(command('extracted-source-tree', ['git', 'write-tree'], source) == SOURCE_TREE, 'EXTRACTED_GIT_TREE_MISMATCH')
        shutil.rmtree(source / '.git')
        report.update(source_file_count=67, original_source_tree=SOURCE_TREE, source_tree_match=True)
        command('readme-sha256sum', ['sha256sum', '--check', 'SHA256SUMS.txt'], package)
        command('entrypoint', [sys.executable, '-m', 'rcc_revas_eval', 'evaluate', '--help'], source)
        command('preflight', [sys.executable, '-m', 'rcc_revas_eval', 'preflight', '--manifest', 'evaluation_manifest.json'], source)
        reproduction = out / 'reproduction'
        command('reproduce', [sys.executable, 'scripts/reproduce_canonical.py', '--output-dir', str(reproduction)], source)
        proof = json.loads((reproduction / 'REPRODUCTION.json').read_text())
        require(proof['status'] == 'PASS' and len(proof['stages']) == 13 and all(x['exit_code'] == 0 for x in proof['stages']), 'REPRODUCTION_FAILED')
        tests = (reproduction / 'tests.stderr.txt').read_text()
        require('Ran 160 tests' in tests and tests.rstrip().endswith('OK'), 'TEST_FAILURE_OR_SKIP')
        metrics = json.loads((reproduction / 'takeshi-report/governance_metrics.json').read_text())
        partner = json.loads((reproduction / 'takeshi-run/run_manifest.json').read_text())
        require(partner['executed_count'] == 36 and partner['error_count'] == 0, 'PARTNER_EXECUTION_FAILURE')
        require(metrics['arm_a']['mismatch_case_ids'] == ['GOV-H06', 'GOV-H07', 'GOV-D08'], 'BASELINE_DIVERGENCE_CHANGED')
        report.update(tests_passed=160, tests_failed=0, reproduction_stages_passed=13,
                      partner_fixtures_executed=36, partner_fixture_errors=0,
                      preserved_partner_label_divergences=metrics['arm_a']['mismatch_case_ids'])
        wheel_source = out / 'wheel-source'
        wheel_source.mkdir()
        for p in members:
            target = wheel_source / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source / p).read_bytes())
        wheelhouse = out / 'wheelhouse'
        command('build-wheel', [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation', str(wheel_source), '-w', str(wheelhouse)], out)
        wheels = list(wheelhouse.glob('*.whl'))
        require(len(wheels) == 1, 'WHEEL_COUNT_MISMATCH')
        with zipfile.ZipFile(wheels[0]) as z:
            modules = [n for n in z.namelist() if n.startswith('rcc_revas_eval/') and n.endswith('.py')]
            require(len(modules) == 17 and all(z.read(n) == (source / n).read_bytes() for n in modules), 'WHEEL_SOURCE_MISMATCH')
        env = out / 'venv'
        venv.EnvBuilder(with_pip=True).create(env)
        py = str(env / 'bin/python')
        command('install-wheel', [py, '-m', 'pip', 'install', '--no-index', '--no-deps', str(wheels[0])], out)
        origin = command('installed-origin', [py, '-c', 'import rcc_revas_eval;print(rcc_revas_eval.__file__)'], out)
        require(str(env) in origin, 'SOURCE_SHADOWED_INSTALLED_WHEEL')
        command('installed-preflight', [py, '-m', 'rcc_revas_eval', 'preflight', '--manifest', str(source / 'evaluation_manifest.json')], out)
        command('installed-takeshi', [py, '-m', 'rcc_revas_eval', 'evaluate', '--manifest', str(source / 'evaluation_manifest.json'), '--input', str(reproduction / 'takeshi-registration/runtime_inputs.jsonl'), '--plan', str(reproduction / 'takeshi-registration/preregistration.json'), '--output-dir', str(out / 'installed-run')], out)
        command('installed-replay', [py, '-m', 'rcc_revas_eval', 'verify-artifacts', '--manifest', str(source / 'evaluation_manifest.json'), '--run-dir', str(out / 'installed-run')], out)
        deterministic = ['rcc_results.jsonl', 'handoff_results.jsonl']
        deterministic += [p.relative_to(reproduction / 'takeshi-run').as_posix() for p in (reproduction / 'takeshi-run/objects').glob('*.json')]
        require(all((reproduction / 'takeshi-run' / p).read_bytes() == (out / 'installed-run' / p).read_bytes() for p in deterministic), 'INSTALLED_RESULT_MISMATCH')
        # Elapsed nanoseconds are measurements, not deterministic content. Preserve both raw receipts.
        source_receipts = [json.loads(line) for line in (reproduction / 'takeshi-run/execution_receipts.jsonl').read_text().splitlines()]
        installed_receipts = [json.loads(line) for line in (out / 'installed-run/execution_receipts.jsonl').read_text().splitlines()]
        require(len(source_receipts) == len(installed_receipts) == 36, 'RECEIPT_COUNT_MISMATCH')
        time_fields = {'runtime_elapsed_ns', 'handoff_elapsed_ns'}
        for left, right in zip(source_receipts, installed_receipts):
            require(all(type(row.get(k)) is int and row[k] >= 0 for row in (left, right) for k in time_fields), 'INVALID_ELAPSED_MEASUREMENT')
            require({k: v for k, v in left.items() if k not in time_fields} == {k: v for k, v in right.items() if k not in time_fields}, 'EXECUTION_RECEIPT_SEMANTICS_MISMATCH')
        report.update(execution_receipt_semantic_matches=36, measured_latency_preserved=True,
                      nondeterministic_receipt_fields=sorted(time_fields))
        require(all(sha((source / p).read_bytes()) == h for p, h in members.items()), 'SOURCE_CHANGED_AFTER_TESTS')
        command('checkout-unchanged', ['git', 'diff', '--exit-code'], checkout)
        report.update(status='PASS', wheel_source_modules_matched=len(modules), installed_deterministic_files_matched=len(deterministic))
    except Exception as exc:
        report.update(status='FAIL', error=type(exc).__name__ + ': ' + str(exc))
    finally:
        (out / 'VERIFICATION.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 2

if __name__ == '__main__':
    raise SystemExit(main())
