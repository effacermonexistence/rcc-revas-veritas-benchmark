# Source publication 0.3.4

This self-contained release contains the reviewed runtime, adapters, schemas,
contracts, tests, example workers, installation scripts and implementation guides.
It was extracted from continuity commit 6f977f1149c9b3363dfd9326d87796dd488cf017
plus the documented 0.3.4 corrections.

Historical run directories mentioned in older audit documents are not included
in this source-only GitHub checkout. They remain in the previously delivered
continuity bundles. Those references are historical provenance, not required
installation dependencies. Current validation is recorded in HANDOFF_ACCEPTANCE.json
and publication-evidence/.

The publication source manifest describes this exact source-only directory,
not the much larger historical continuity archive. Native third-party source
checkouts and optional dependencies must be obtained using SOURCES_NATIVE.json
and scripts/bootstrap_native.sh; they are not redistributed here.

New pilot: install this directory, run `rveval init-pilot --pilot-id pilot-name
--output-dir ../pilot-name`, then follow the generated START_HERE.md. The output
is an explicitly labeled engineering starting point, not a completed integration
with an arbitrary future benchmark.
