# 0.1.0 build and reproduction

The rc2 source was cloned from the supplied local Git bundle. Its original ZIP,
wheel and audit remain unchanged. Current runtime fixes are covered by executable
regression tests; old generated rc2 review outputs were removed from this tree
and remain available in Git history and the original artifacts.

`python scripts/reproduce_canonical.py --output-dir <new-dir>` is the complete
local review command. It does not silently repair a changed source manifest.
`python scripts/freeze_sources.py` is an author-time release operation only;
never use it to conceal failed verification. Release evidence records the
source manifest used for each test/run and exact committed source separately.

The fixture was materialized from the fetched upstream blob and verified against
the full 114,884-byte Git object identity, not a three-case approximation.
Transport tests use clearly labelled loopback peers, not a substituted native
VERITAS runtime. All evidence of real HTTP is reported with that test origin.
