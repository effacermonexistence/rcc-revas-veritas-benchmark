# 0.2.1 再監査後の追加事項

この版では、従来の101件のテストだけでは検出できなかった問題を追加テストで確認し、修正しています。実装時は以下を必ず反映してください。既存の36-case結果は変更しません。

**採点はコーパス全体の実行後です。** 1ケースのA/B終了直後に採点して次のケースへ進む方式ではありません。すべてのケース、反復、A/Bとreplayを終了してから、採点、比較、集計を行います。`state`、`apply`、`seal_score`で正解やjudgeの結果を計算・返却しないでください。

**大きな環境は採点用の状態だけを分離します。** Pythonでは`defer_score()`が`DeferredScore`を返します。`fingerprint()`、`score()`、`close()`を実装してください。RPCでは`deferred_scoring_supported: true`と`seal_score`、`score_fingerprint`、`score_sealed`、`close_score`を使います。元の環境をcloseしても、採点用tokenと固定済みの状態は有効でなければなりません。作成時に採点してはなりません。

**A/Bの初期条件はhashだけでなく、task、tools、agent_state、governance_contextも一致させます。** `snapshot()`または1回のRPC state応答で整合した状態を返してください。`terminal`はBooleanのみです。文字列の`"false"`やnullは受理されません。

**RPC切断後の自動再接続はありません。** エラーになったプロセスとsession tokenは再利用できません。復旧は元のjournalを保存した別attemptとして扱います。contextに既存のcandidate/state/RCC hashがある場合、不一致を上書きして修復したように見せないでください。

**失敗した実行は正常な集計に混ぜません。** 集計callbackには有効な比較対象だけが渡ります。全登録件数と除外された件数・IDは別に保存されます。条件付きの集計を全母集団の結果と呼ばないでください。

**本番の外部評価前にnative acceptance packetが必要です。** `FINAL_RUN_GATE.md`の形式で、実際のRCC/VERITAS経路、公式scorerとの一致、candidate/state binding、single dispatch、framework acceptanceの5つの記録とraw logのhashを提出してください。各記録をexact configとprofile subjectに結び付けます。`rveval readiness`はその完全性とbyteの一致を確認しますが、実行を独立に証明するものではありません。未設定のtemplateは意図的にNOT_READYになります。

英語の`TAKESHI_IMPLEMENTATION_GUIDE.md`、`IMPLEMENTATION_GUIDE.md`、`COMMAND_RPC_PROTOCOL.md`、`FINAL_RUN_GATE.md`を実装契約としてください。以下の既存ガイドもこの追加事項と合わせて読んでください。

---

# Takeshiさん向け実装入口 — v0.2.1

技術上の正本は英語の `TAKESHI_IMPLEMENTATION_GUIDE.md` と
`IMPLEMENTATION_GUIDE.md`、`COMMAND_RPC_PROTOCOL.md` です。
このファイルは、実装を始める順序と、推測して埋めてはいけない境界を整理します。

## 今回作ったもの

特定の36ケースやAgentDojoだけに固定しない評価基盤です。
Pythonプラグイン、常駐JSON RPCワーカー、既存のネイティブループに挿入する
`NativeGovernanceHook` を用意しています。ソースと入力のfreeze、候補と状態の
対応確認、エラーの分離、採点の後段化、証拠ファイルの検証まで実装しています。

ただし、すべての外部ベンチマークの依存関係・モデル・公式採点器を同梱したもの
ではありません。デモのPassThroughRCCやAllowAllVeritasを実際のRCC/VERITASとして
報告しないでください。ネイティブ実装との接続は別途、実行証拠付きで確認します。

## 最初に実行すること

```bash
python -m pip install -e '.[test]'
python scripts/verify_source_manifest.py
python scripts/run_acceptance.py --output /absolute/path/to/new-output
```

`examples/rpc/worker.py` は常駐ワーカーの完全に実行可能な例です。
JavaScript側の例は `examples/rpc/agent.mjs` です。
このプロトコルを維持し、各roleの中身を実際のネイティブ呼び出しへ置き換えてください。

## 既存のAgentDojo実装は再利用対象です

`veritas_os/benchmarks/agentdojo_banking_adapter.py` と
`agentdojo_banking_same_candidate.py` は既に存在します。
「joint repoにAgentDojo adapterがない」という事実を、VERITAS全体に存在しない
という意味に拡張しません。既存のcapture、candidate freeze、pre-state clone、
BindAdapterの経路を確認し、今回のRCC採用済みcandidateへ接続してください。

ただし既存のBanking用 `TASK_MUTATION_POLICY` は別のsuiteや新しいtaskの汎用policy
ではありません。task 3/4/15などの条件を、そのまま全ベンチマークへ移さないでください。

## 比較を三種類に分けます

1. live: 同じ初期条件からA/Bを独立実行。介入後はモデルの後続trajectoryが異なってよい。
2. fixed_replay: Aの同じRCC採用candidateと同じ公開governance contextでgateのみを再評価。
   これはBのwhole-task scoreを作りません。
3. immediate-effect pair: 復元可能なsandboxを二つ作り、同一candidateによる直後のeffectを
   native側とVERITAS側で比較。これもwhole-task utilityとは別です。

## 実装時に必ず分離するもの

ユーザーが要求した操作とモデルが提案した操作、公開観測と非公開評価状態、
RCCのhashとVERITASのcanonical hash、候補採用と実行権限、HTTP成功とnative消費、
Bind判定と実際のapply、apply試行と観測されたeffectを分離してください。

AuthorityEvidenceやHuman Approvalは独立したネイティブ検証経路から取得します。
正解ラベルからauthority_validを作ったり、approval不要の場合に架空の承認証拠を
作ったりしないでください。未実装はUNSUPPORTED、通信失敗はERRORです。
それらを正当なBLOCKとして数えません。

ネイティブBindが既にsandbox applyを実行する場合、基盤側で二重にapplyしないよう
実行主体を一つに決めてください。private checkpointは復元担当側に保持し、
モデルやgateへ必要以上の評価情報を渡さないでください。

## Benへ返すもの

実際のcommit・entrypoint・実行コマンド、入力出力mapping、native trace、
候補と状態のhash対応、権限/承認/policyの出典、開発用positive/negative test、
公式scorerとの一致確認、依存関係と未解決項目、最終freeze案を返してください。
未解決項目は必要field・owner・理由まで特定し、既に文書化された全体説明を
最初から繰り返し求める必要がない形にしてください。

旧36-caseのadverse結果と修正版の結果は変更せず保存します。
外部評価の最終結果を見る前に、新しいsource / adapter / model / scorer / contractを
固定してください。開発結果を見て修正した場合は、新versionとして履歴を残します。
