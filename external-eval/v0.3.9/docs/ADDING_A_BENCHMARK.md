# Add a benchmark — current v0.3.3

Use `TAKESHI_IMPLEMENTATION_v0.3.3.md` as the executable contract. Choose by native
API rather than by benchmark name. Existing step/RPC adapters remain supported.
Existing SDKs retain their loop with NativeGovernanceHook/NativeBindExecutor.
A whole native command uses `native-job/v1` through the common freeze/run/verify/
matrix commands; see `examples/native_job/config.json` and its running worker.

Keep official scorer/aggregation, exact native input/output, independent request
and authority, complete enrollment and source/dependency pins. A new API requires
an explicit wrapper; a new task set using the same API reuses the wrapper.
Do not modify the core to hardcode task IDs or expected labels.

`contracts/VERITAS_MAPPING_v0.3.3.json` answers Q1–Q9 and pins ownership/field meanings.
`mapping-check` tests its completeness; actual native test traces establish its
runtime scope. `benchmark_fitness` records purpose-specific validity separately
from whether a command executed. A contaminated benchmark is not rehabilitated
by a successful installation check.
