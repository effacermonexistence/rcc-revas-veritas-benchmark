# Follow-up: scoped publication permission and historical identifiers

This documentation update responds to [Takeshi's latest comment](https://github.com/veritasfuji-japan/rcc-revas-veritas-benchmark/pull/590#issuecomment-6813123141), posted at `2026-11-12T03:03:28Z`. It publishes a sanitized account of the contributor's November 12 local investigation and records the permission now granted. It does not reopen the completed archive audit, rerun experiments, or change historical evidence. **The merge hold remains.**

## Publication permission: the six identified files only

Takeshi states that he was the primary creator of the five upstream benchmark modules and the #466 source document, and that no third-party code was copied into those materials without authorization. These are the maintainer's statements, not a new independent authorship investigation by the contributor.

For the rights he controls, he permits inclusion of those files **solely in the existing PR #590 historical research-evidence archive identified by its current evidence manifest**, for preservation and review. The contributor's independently authored contributions remain the contributor's IP. This permission does not transfer copyright, establish a general open-source license, authorize unrelated reuse or redistribution, extend to VERITAS Core or other repositories, or grant rights over third-party material.

| Identified material | SHA-256 already recorded for the archived bytes |
| --- | --- |
| `agentdojo_constraint_resolver_v0_1.py` | `99b44833a38114c35c2f33181c3530edac6267ac5a7f3a0ca2bff5846b4c150f` |
| `original_request_authority_lineage_v1.py` | `f35ae275c848610fd7435c69d69b9a59b45dcdeb1312193e908d5c88988df0de` |
| `scripts/agentdojo_clean_ab_canonical_final_runner_v2_8.py` | `b04f7b966f5bbeba89b696032a5d1273a03bd997117af997174d30daff486dea` |
| `scripts/agentdojo_final_runner_integration_v0_1.py` | `c9e7390e432647bfa7e45ea9f905cab25d415038871d40db93ffc17dd7f9b8a1` |
| `scripts/agentdojo_openai_frozen_adapter_v0_1.py` | `45fe1e791d1df72f883d1817eb0f5a601427c3d3a51603c49e8ec10da807efad` |
| `evidence/current-approved/UPSTREAM_466_SOURCE.md` | `0669fb2d83ca7d7a1723f4d23d76d251b4bbf8b34d2843eb0b350b3c63aa94c0` |

The maintainer separately reports recalculating all six hashes against the pinned upstream files and finding that they match the manifest. That establishes his reported upstream-to-manifest identity check; it is not a ZIP-content check or independent reproduction. The earlier pending-permission status is superseded **only for these files and this purpose**. The dated [November 11 observed review](../audit-20261111/observed/publication-review.json) is preserved unchanged as a historical observation.

## Two identifiers: observed role versus capability status

The identifiers are called **ID-A** and **ID-B** here. Neither raw value, a fragment of either value, private app-record content, nor an original approval export is published by this update.

| Identifier | Verified origin and purpose | Executable use in the inspected research path | Capability classification |
| --- | --- | --- | --- |
| ID-A | Original `request_user_input_async` call ID and corresponding app question-item ID, retained as `OWNER_QUESTION_ANCHOR.question_id` | The reader uses it in the parameterized local question lookup and exact reply-to-question comparison. It is an approval correlation/selector input, not an unused display label. | **UNKNOWN** beyond the inspected path. No standalone credential/bearer use was found in that local research path. |
| ID-B | App item ID of the actual user reply, copied to `decision_source.message_id` | The reader records the message ID after parsing the reply. The runtime compares the complete decision-source record for continuity, so the ID participates indirectly in that comparison. | **UNKNOWN** beyond the inspected path. Observed use is provenance/continuity, not a standalone credential. |

The origin of each value was established from its actual record role, not inferred from its format. The identifier-generation implementation and all app/server interfaces were not available for authoritative assessment. Neither is certified to be strictly harmless or incapable of capability use.

### Evidence supporting these bounded findings

The contributor's November 12 read-only investigation found:

1. The anchored local history contained exactly one matching question item and one matching actual user-reply item. The question matched the preserved anchor, text and options; the reply linked to that question.
2. The database reply's raw JSON was byte-identical to the privately preserved export and matched its recorded source hash. This is local provenance consistency, not independent human/issuer authentication.
3. The original rollout corroborated both events. Full reply-object equality initially failed because the rollout used `UserMessage` and `client_id`, while the database/export used `userMessage` and `clientId`. After only those two explicit representation transformations, all fields agreed. The raw originals were not modified; representation equality is not reported as byte equality.
4. The inspected reader and runtime were byte-identical to the corresponding Nano and Mini frozen source snapshots. Their already-public identities are shown below.
5. A scoped exact-value search found 11 matching files in the relevant local research, publication-preparation and prior-audit directories. Its exclusions included archives, databases, Git internals and dependency environments; the relevant database and original rollout were read separately. This is not an exhaustive filesystem/server search or proof of capability absence.
6. A bounded inspection of the current local packaged client JavaScript supported the question/reply correlation role. It was not a review of the complete historical client, native code, or service-side credential/authorization verifier. No app source is newly redistributed here.

The local command templates were `rg --files-with-matches --hidden --fixed-strings --file - <scoped roots>` with privately supplied stdin patterns; a SQLite `mode=ro` connection with `PRAGMA query_only=ON` and a parameterized `WHERE thread_id=? AND item_id=?` query; sequential reads of the original rollout; and static source/hash comparisons. No raw identifier was placed in command arguments or published outputs. The complete sanitized internal investigation records remain private. A public reader cannot independently repeat the private-original checks from this public subset.

| Archived research source | SHA-256 | Relevant locations |
| --- | --- | --- |
| `research_owner_decision_v1.py` | `93abb89d2ecaf128f861dd61f12e89216944729a15833d5cd2f1d6c1b83bf412` | Lines 25–49: reply parsing/correlation; 62–104: thread/question/proposal/source checks |
| `owner_approved_research_runtime_v1.py` | `fee163e1eec28dc79f34a9128ee97f56d64b83af60d3179fc40037185681ab0d` | Lines 45–105: enrollment, current source and signed grant; 163–176 and 239–260: scope and Native Bind checks |

These files are already in `SNAPSHOT.zip` under `evidence/current-approved/review-code/` and both `evidence/current-approved/approved-runs/*/source-snapshot/` paths. They were inspected as source; this follow-up does not import or execute the reader, issue approvals, generate grants or replay protected actions.

In that source, the identifier alone is insufficient: checks also require the anchored thread and question, proposal/review-document hashes, complete reply shape/text/answer and current decision. The runtime separately binds signed scope, research date, consumption ledger and Native Bind. Signed grants bind the source-record hash, not either identifier as a private signing key. Mutable local history is not independent authentication: an actor able to forge trusted local records presents a separate trust-boundary concern. No such forgery or exploit was attempted or demonstrated.

### Why the literals appeared in public history

Both values were inserted into the publication scanner and original inspection helper as **negative-match privacy patterns** intended to reject private identifiers in the archive. Including the raw patterns in source exposed the metadata the scanner sought to withhold. That scanner use is not an authentication request or an executable approval grant.

The historical helper in `4328be1d35d6494458708af6bd85a62d837aa8ca` contains one literal occurrence of each value. The correction at `e499c67bd78c25da438e9fc3acb9db1ec870342a` uses digest matching and has no raw occurrence of either in the current helper. The earlier [redaction check](../audit-20261111/observed/identifier-redaction-check.json) records that scanner correction. **The old commit still contains the values; current-source redaction is not history erasure.**

## Security impact and recommended history treatment

Exposure creates private-record/approval linkability and target-identification risk. ID-A also participates in the inspected approval-correlation path. No credential exploitation was established. Whether either value can authorize a read, edit, reply/replay or other action through an uninspected interface remains **UNKNOWN**; a scoped negative search cannot close that question.

| Possible response | Assessment and authorization boundary |
| --- | --- |
| Keep current redaction and private evidence | Recommended now. Preserve source provenance privately and publish labels/limits instead of raw metadata. |
| Retain history with documented limitations | An option after adequate non-capability confirmation and the owner's acceptance of residual privacy/linkability exposure. This update does not declare that decision made or the security issue resolved. |
| Revoke or rotate | Assess only if an actual capability, its issuer and its target are established. Do not assume these references are API keys or rotate unrelated credentials. Execution requires explicit authorization. |
| Coordinated history rewrite | Propose if capability exposure or the owner's privacy decision warrants it. Requires explicit owner/maintainer authorization, preserved private originals/hashes, and coordination over fork/PR refs and cached copies. Rewriting history does not itself revoke a capability or erase all copies. |

**Current recommendation:** maintain the merge hold, private evidence and current redaction; obtain an authoritative disposition of the uninspected capability boundary and an owner/maintainer decision on historical metadata. No destructive treatment has been selected or executed by this update.

## Unchanged checks and remaining work

The [completed archive/grant audit](../audit-20261111/README.md) remains its previously recorded stored-evidence verification. This follow-up does not rerun it or claim a new Native score, independent reproduction, held-out result or Task1 G vs G+P result. The original ZIP, manifest, score files, CSVs, signed payloads, experimental logic and authorization conditions are unchanged. No broad workflow approval, merge, revocation, credential rotation or history rewrite is performed.

Remaining items are the two **UNKNOWN** capability classifications, final owner/maintainer history disposition, and the independent-verification/security checks explicitly retained by Takeshi. The limited six-file publication permission does not resolve those separate questions.

**日本語要約:** 最新コメントの許諾は、現manifestの5モジュールと#466文書を既存PR #590の履歴証拠として保存・レビューする範囲だけに反映しました。ID-Aは承認質問の呼出し／質問ID、ID-Bは実際の回答メッセージIDです。ローカルでの出所・照合用途は確認しましたが、未調査のapp/server境界で認証・認可能力を持たないとは断定できず、両方ともUNKNOWNです。値は再掲していません。現行redactionとmerge holdを維持し、履歴の最終処理はowner/maintainerとの合意事項として残します。新規実験・権限変更・履歴書換えは行っていません。
