# v0.3.4 — portable pilot handoff

* Reproduced all 12 mapping rows failing outside the original source checkout.
* Own code_refs now resolve against the actually loaded rveval library and return source hashes.
* Invalid mapping identifiers/owners/transforms/ref structures/question maps return FAIL rather than type crashes.
* Added init-pilot with packaged schemas, mapping, source-pinned worker, native implementation hooks and bilingual docs.
* Added 19 portability and error-path regressions.
* Replaced ambiguous stacked README versions with one current entrypoint.
* Prior historical result files, claims and source pins are preserved.
