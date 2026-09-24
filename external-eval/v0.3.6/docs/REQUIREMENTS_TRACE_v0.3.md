# Source-to-implementation trace — native release 0.3

| Required boundary from the joint materials | Concrete implementation / evidence |
|---|---|
| Adopted candidate is not execution authority | ExternalRCCGate handoff flags; NativeBindExecutor separate effect owner |
| Same exact proposed operation | CandidateAction digest, hook.verify_dispatch, native callback substitution guards |
| Same pre-state, not a label-filled policy | private snapshot versus public context; clone/effect proof remains separately scoped |
| Native authority and approval ownership | NativeAuthorityResolver calls actual verifier/runtime validator; independently configured issuers/contracts |
| No fabricated approval-not-required evidence | Native action contract requirement, not absence of receipt |
| Preserve bad/neutral results | historical evidence plus versioned validation attempts retained |
| Original labels remain scorer-only | cohort-wide delayed scoring; Instance.doc withheld; tau oracle replay not intercepted |
| Native benchmark semantics | native framework wrappers, official output parsing, benchmark-owned scorer |
| Not another 36-case runner | listed catalogue, arbitrary enrolled count, no case ID selection in core |
| Actual invocation versus metadata | executed native tests, signed BindReceipt, direct sandbox mutation and installed-wheel runs |
| Failure is not a successful block | GovernanceStop versus integrity/infrastructure exceptions; unknown effect after interrupted apply |
| No hidden retry | persistent local OperationLedger; invalid IDs rejected; failed/cancelled attempt not regenerated |
| Runnable partner handoff | bootstrap, validate_native, standalone signed example, English/Japanese guides and actual API signatures |
| Preserve historical source version | old RCC pin unchanged; new ExternalRCCGate source/policy identity is separate |
| Scope of contribution | native boundary PASS is not whole-task uplift, private-production parity or universal validation |

The common-core contract and original Takeshi materials are design sources; they
are not used as evidence that an unexecuted native path ran. `SOURCE_REVIEW.md`
retains historical source references; `SOURCES_NATIVE.json` pins the actual native
source used for this release. `NATIVE_COVERAGE.json` names tested versus untested
native scope explicitly.
