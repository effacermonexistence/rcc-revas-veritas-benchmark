"""One-time byte-preserving publication repair; never changes runtime policy."""
from __future__ import annotations
import gzip, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path.cwd()
PACKAGE = ROOT / 'rcc-revas-eval/v0.1.0'
ARCHIVE_NAME = 'rcc-revas-eval-v0.1.0-source.tar.gz'
EXPECTED = '4c736357ab93a8f4b5027b94c20340b973c760de1a0027df30bb53d3d10f47d8'
EXPECTED_TREE = 'ab477cff7924b922b0885fb665e5ca0d6e42868a'
SOURCE_COMMIT = '8692c48bc4f93b56ab019004c27b7c6fd9c8fe62'
OLD_PUBLICATION = '4f6996329ec49c4968545e0c0235d463225d88b3'
OLD_BAD_DIGEST = '2ddccc871649b9a8d0f7630faace8918215d7c07b50a6ed9be119af6e661cf6a'

def run(args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def extract(data, dest):
    dest.mkdir(parents=True, exist_ok=False)
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tf:
        for member in tf.getmembers():
            name = Path(member.name)
            if name.is_absolute() or '..' in name.parts or '.git' in name.parts:
                raise RuntimeError('UNSAFE_ARCHIVE_PATH')
            if member.name in seen:
                raise RuntimeError('DUPLICATE_ARCHIVE_PATH')
            seen.add(member.name)
            path = dest / name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tf.extractfile(member).read())
                path.chmod(0o755 if member.mode & 0o111 else 0o644)
            else:
                raise RuntimeError('NON_REGULAR_ARCHIVE_MEMBER')

def tree_identity(directory):
    run(['git', 'init', '-q'], directory)
    run(['git', '-c', 'core.autocrlf=false', 'add', '-f', '.'], directory)
    tree = run(['git', 'write-tree'], directory)
    shutil.rmtree(directory / '.git')
    return tree

def main():
    work = Path(os.environ['RUNNER_TEMP']) / ('rcc-repair-' + os.environ['GITHUB_RUN_ID'])
    work.mkdir(exist_ok=False)
    url = os.environ['RCC_ARCHIVE_TRANSPORT_URL']
    # The short-lived URL grants read access only to this archive already authorized for publication.
    # It is transport only: the independent SHA-256 and original Git tree are authoritative.
    with urlopen(Request(url, headers={'User-Agent': 'OmarAGI-publication-repair'}), timeout=60) as response:
        data = response.read(2_000_000)
    if len(data) != 109796 or hashlib.sha256(data).hexdigest() != EXPECTED:
        raise RuntimeError('TRANSPORT_ARCHIVE_HASH_OR_LENGTH_MISMATCH')
    gzip.decompress(data)  # Verifies stream EOF, CRC and length.
    source = work / 'source'
    extract(data, source)
    files = sorted(p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file())
    if len(files) != 67 or tree_identity(source) != EXPECTED_TREE:
        raise RuntimeError('ORIGINAL_SOURCE_TREE_MISMATCH')
    run([sys.executable, '-m', 'rcc_revas_eval', 'evaluate', '--help'], source)
    run([sys.executable, '-m', 'rcc_revas_eval', 'preflight', '--manifest', 'evaluation_manifest.json'], source)
    evidence = work / 'reproduction'
    run([sys.executable, 'scripts/reproduce_canonical.py', '--output-dir', str(evidence)], source)
    report = json.loads((evidence / 'REPRODUCTION.json').read_text())
    if report['status'] != 'PASS' or len(report['stages']) != 13 or any(s['exit_code'] for s in report['stages']):
        raise RuntimeError('CANONICAL_REPRODUCTION_FAILED')
    tests = (evidence / 'tests.stderr.txt').read_text()
    if not re.search(r'Ran 160 tests', tests) or not tests.rstrip().endswith('OK'):
        raise RuntimeError('TEST_COUNT_OR_TEST_SUCCESS_MISMATCH')
    partner = json.loads((evidence / 'takeshi-run/run_manifest.json').read_text())
    metrics = json.loads((evidence / 'takeshi-report/governance_metrics.json').read_text())
    if partner['executed_count'] != 36 or partner['error_count'] != 0:
        raise RuntimeError('PARTNER_FIXTURE_EXECUTION_FAILED')
    if metrics['arm_a']['mismatch_case_ids'] != ['GOV-H06', 'GOV-H07', 'GOV-D08']:
        raise RuntimeError('BASELINE_POLICY_OR_LABELS_CHANGED')
    # Check all original source bytes are still identical after testing.
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tf:
        for m in tf.getmembers():
            if m.isfile() and (source / m.name).read_bytes() != tf.extractfile(m).read():
                raise RuntimeError('SOURCE_MUTATED_DURING_TESTS')
    archive = PACKAGE / 'source' / ARCHIVE_NAME
    archive.write_bytes(data)
    runtime = PACKAGE / 'runtime'
    if runtime.exists():
        raise RuntimeError('UNEXPECTED_EXISTING_RUNTIME_DIRECTORY')
    extract(data, runtime)
    pin = json.loads((PACKAGE / 'CANONICAL_PIN.json').read_text())
    pin.update(source_archive_sha256=EXPECTED, source_archive_size_bytes=len(data),
               local_canonical_source_commit=SOURCE_COMMIT, source_git_tree=EXPECTED_TREE,
               expanded_source_path='rcc-revas-eval/v0.1.0/runtime', source_file_count=67,
               publication_revision=2, supersedes_publication_commit=OLD_PUBLICATION,
               runtime_code_changed=False, policy_or_gold_labels_changed=False)
    write_json(PACKAGE / 'CANONICAL_PIN.json', pin)
    (PACKAGE / 'SHA256SUMS.txt').write_text(EXPECTED + '  source/' + ARCHIVE_NAME + '\n')
    file_hashes = {name: hashlib.sha256((runtime / name).read_bytes()).hexdigest() for name in files}
    write_json(PACKAGE / 'SOURCE_FILES.sha256.json', file_hashes)
    receipt = {'status': 'PASS', 'kind': 'PUBLISHER_CI_VERIFICATION_NOT_PARTNER_VERIFICATION',
               'source_commit': SOURCE_COMMIT, 'source_git_tree': EXPECTED_TREE,
               'archive_sha256': EXPECTED, 'archive_bytes': len(data), 'source_files': len(files),
               'original_source_tree_match': True, 'runtime_code_changed': False,
               'tests_passed': 160, 'tests_failed': 0, 'reproduction_stages_passed': 13,
               'partner_fixtures_executed': 36, 'partner_fixture_errors': 0,
               'partner_label_matches': metrics['arm_a']['exact_label_agreement']['numerator'],
               'preserved_partner_label_divergences': metrics['arm_a']['mismatch_case_ids'],
               'native_VERITAS_executed': False, 'joint_contract_frozen': False,
               'python': sys.version, 'workflow_run_id': os.environ['GITHUB_RUN_ID'],
               'workflow_commit': os.environ['GITHUB_SHA'],
               'workflow_url': 'https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID']}
    write_json(PACKAGE / 'PUBLICATION_VALIDATION.json', receipt)
    (PACKAGE / 'PUBLICATION_CORRECTION.md').write_text(
        '# Publication correction, revision 2\n\n'
        'The archive in publication commit `' + OLD_PUBLICATION + '` was truncated during the publisher upload. '
        'Its actual SHA-256 was `' + OLD_BAD_DIGEST + '`, not the declared digest. '
        'Takeshi correctly stopped before extraction or execution.\n\n'
        'This revision replaces the invalid archive. The recovered original source is unchanged: '
        'all 67 files produce Git tree `' + EXPECTED_TREE + '` from source commit `' + SOURCE_COMMIT + '`. '
        'No runtime rule, original fixture, label, or three-case semantic divergence was retuned.\n\n'
        'The newly packaged archive digest is `' + EXPECTED + '`. Do not substitute the corrupted archive digest '
        'or continue using the superseded publication pin. Publisher-side CI has checked archive integrity, '
        'source tree identity, all 160 tests, and the 13-stage reproduction. '
        'Partner independent verification and the native joint evaluation remain subsequent steps.\n')
    (PACKAGE / 'README.md').write_text(
        '# RCC/REVAS canonical runnable v0.1.0 — corrected publication\n\n'
        'Publication revision 2. Runtime source commit: `' + SOURCE_COMMIT + '`.\n\n'
        'Source Git tree: `' + EXPECTED_TREE + '`. All 67 original source files are unchanged.\n\n'
        'Archive: `source/' + ARCHIVE_NAME + '`\n\n'
        'Archive SHA-256: `' + EXPECTED + '` (' + str(len(data)) + ' bytes).\n\n'
        'The same source is also directly inspectable in `runtime/`.\n\n'
        '## Reproduce from the archive\n\n'
        'From this package directory, using Python 3.11+:\n\n'
        '```bash\nsha256sum --check SHA256SUMS.txt\n'
        'mkdir extracted\ntar -xzf source/' + ARCHIVE_NAME + ' -C extracted\ncd extracted\n'
        'python -m rcc_revas_eval evaluate --help\n'
        'python -m rcc_revas_eval preflight --manifest evaluation_manifest.json\n'
        'python scripts/reproduce_canonical.py --output-dir ../reproduction-new\n```\n\n'
        'Alternatively `cd runtime` and run the same Python commands; no archive is needed for inspection. '
        'For all optional JSON-schema tests, install `jsonschema`; the runtime itself has no third-party dependencies. '
        'A new reproduction output directory is required.\n\n'
        'Verified entrypoint: `python -m rcc_revas_eval evaluate`. Detailed manifest/input/plan arguments '
        'and the complete execution path are documented in `runtime/README.md`.\n\n'
        '## Validation\n\n'
        'See `PUBLICATION_VALIDATION.json` for the actual publisher CI run and `SOURCE_FILES.sha256.json` '
        'for every source file digest. 160 tests passed and all 36 original partner fixtures executed/replayed. '
        'The three original label divergences GOV-H06, GOV-H07 and GOV-D08 are preserved. '
        'These are not native joint VERITAS results.\n\n'
        'This correction supersedes publication `' + OLD_PUBLICATION + '`. '
        'See `PUBLICATION_CORRECTION.md`. The subsequent `GITHUB_PUBLICATION.json` records the corrected immutable publication pin.\n')
    for name in ('GITHUB_PUBLICATION.json', 'CANONICAL_GITHUB_PIN.md'):
        (PACKAGE / name).unlink(missing_ok=True)
    run(['git', 'config', 'user.name', 'github-actions[bot]'])
    run(['git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com'])
    run(['git', 'add', '-f', '--', 'rcc-revas-eval/v0.1.0'])
    run(['git', 'commit', '-m', 'Fix truncated RCC canonical archive; preserve all original runtime bytes'])
    corrected = run(['git', 'rev-parse', 'HEAD'])
    publication = {'schema_version': 'rcc-revas.github-publication.v1',
                   'canonical_source_commit': corrected, 'canonical_source_tree': run(['git', 'rev-parse', 'HEAD^{tree}']),
                   'canonical_source_path': 'rcc-revas-eval/v0.1.0',
                   'verified_entrypoint': 'python -m rcc_revas_eval evaluate',
                   'local_source_commit_preserved_in_release_metadata': SOURCE_COMMIT,
                   'source_git_tree': EXPECTED_TREE, 'source_archive_sha256': EXPECTED,
                   'publication_repository': os.environ['GITHUB_REPOSITORY'], 'publication_branch': 'main',
                   'supersedes_publication_commit': OLD_PUBLICATION, 'publication_revision': 2,
                   'joint_contract_frozen': False, 'native_veritas_joint_run_completed': False}
    write_json(PACKAGE / 'GITHUB_PUBLICATION.json', publication)
    (PACKAGE / 'CANONICAL_GITHUB_PIN.md').write_text(
        '# Corrected canonical publication pin\n\n`' + corrected + '`\n\n'
        'https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/tree/' + corrected + '/rcc-revas-eval/v0.1.0\n\n'
        'Entrypoint: `python -m rcc_revas_eval evaluate`\n\nArchive SHA-256: `' + EXPECTED + '`\n\n'
        'Original runtime source is unchanged. This supersedes `' + OLD_PUBLICATION + '`.\n')
    run(['git', 'add', '--', 'rcc-revas-eval/v0.1.0/GITHUB_PUBLICATION.json', 'rcc-revas-eval/v0.1.0/CANONICAL_GITHUB_PIN.md'])
    run(['git', 'commit', '-m', 'Record corrected immutable RCC publication pin'])
    run(['git', 'push', 'origin', 'HEAD:main'])  # Fast-forward only; never force.
    # Fetch from the remote, not from the download or the working tree.
    run(['git', 'fetch', 'origin', 'main'])
    published = subprocess.check_output(['git', 'show', 'origin/main:rcc-revas-eval/v0.1.0/source/' + ARCHIVE_NAME])
    if published != data or hashlib.sha256(published).hexdigest() != EXPECTED:
        raise RuntimeError('POST_PUBLICATION_READBACK_MISMATCH')
    write_json(work / 'REMOTE_READBACK.json', {**receipt, 'canonical_publication_commit': corrected,
               'metadata_commit': run(['git', 'rev-parse', 'HEAD']), 'remote_archive_byte_match': True})
    print(json.dumps({'corrected_commit': corrected, 'archive_sha256': EXPECTED, 'remote_readback': 'PASS'}))
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('evidence_dir=' + str(work) + '\n')

if __name__ == '__main__':
    main()
