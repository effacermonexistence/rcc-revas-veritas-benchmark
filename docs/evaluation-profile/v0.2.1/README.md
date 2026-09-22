# VERITAS evaluation profile

**0.2.1-docs-review — documentation only; not the canonical executable RCC release.**

Start with [EVALUATION_PROFILE.md](EVALUATION_PROFILE.md). It preserves the existing two-condition comparison: RCC/REVAS versus the same RCC/REVAS plus current VERITAS full treatment. It references the reusable partner core rather than redefining it.

[CORE_REFERENCE.json](CORE_REFERENCE.json) pins the shared core's exact bytes and publication commit. [profile.json](profile.json) separates documented conditions from unresolved runtime values. [PUBLICATION_CHECK.json](PUBLICATION_CHECK.json) records the limited checks performed for publication. See [NOTICE.md](NOTICE.md) for disclosure and rights scope.

No runner, dataset, existing contract or runtime code is replaced by this directory. The proposed `rcc_revas_eval` commands are not implemented here. This publication does not complete the requested canonical executable commit/entrypoint handoff or mark a clean benchmark as executed.

**Shared partner-kit entry:** [read the exact referenced common release](https://github.com/effacermonexistence/omaragi-reliability-replay/tree/aeed640a54d8956e32a6234d78b5f4314c6e96e2/partner-kit/v0.3).
