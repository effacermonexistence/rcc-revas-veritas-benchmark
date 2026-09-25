# Current architecture v0.3.3

Read TAKESHI_IMPLEMENTATION_v0.3.3.md and the executable mapping contract.
The common freeze/run/verify/matrix surface accepts step/RPC adapters AND native-job/v1.
The native-job backend keeps native scheduling/objects/scoring and separates execution
from scoring by a sealed artifact barrier. Native hooks and SDK wrappers remain
available without requiring a conversion into a universal reset/step simulator.

The two acceptance axes are extension protocol correctness and partner mapping
completeness. Benchmark fitness, full task/model coverage, native authenticity,
and private production parity remain separate propositions.

All cases/trials/arms in one job finish before that job scores. A catalogue freezes
all inputs first but each independent job has its own scoring barrier; coupled
adaptive studies must place the whole cohort in one two-phase native job or enforce
an equivalent native barrier. Process separation is not a hostile-code sandbox.
