# Takeshiさん向け実装・再現手順 v0.3.2

今回の更新では、単にテスト件数を増やすのではなく、未接続だった native
`/v1/decide` から実際の Bind と暗号化 TrustLog までの経路を接続しています。
正確な callback 契約と全手順は同名の英語版を canonical reference としてください。
既存の v0.3.0 / v0.3.1 の結果は過去の記録として保持しています。

## まず実行するもの

依存関係とソースの準備は `bash scripts/bootstrap_native.sh` です。
表示される `scripts/validate_native.py` コマンドを実行すると、依存関係検査、
全体テスト、native 統合テスト、実データ評価が実行されます。
出力先は毎回新しいディレクトリにしてください。

完全な native 接続は、次の独立したスクリプトでも再現できます。

```
export PYTHONPATH="$PWD/src:/sources/veritas_os"
python examples/native_decide_bind/sandbox.py --veritas-root /sources/veritas_os --mode valid --output /results/full-valid-new
python examples/native_decide_bind/sandbox.py --veritas-root /sources/veritas_os --mode tampered --output /results/full-tampered-new
python examples/native_decide_bind/sandbox.py --veritas-root /sources/veritas_os --mode revoked --output /results/full-revoked-new
```

valid は counter を一度だけ更新します。署名改ざんと権限失効は native BLOCKED
となり、counter を変更しません。認証、署名付き compiled policy、kernel、CDA、
promotion、RuntimeAuthorityValidator、Bind、暗号化保存は native コードです。
LLM provider の返答だけは固定 transcript にした工学的な接続試験です。
モデルの実力評価、全 production branch、WORM 保証とは区別してください。

## 本番のベンチマークに接続する場所

`NativeDecisionIntentFactory` を `NativeBindExecutor.intent_factory` に渡します。
`post(payload)` は認証した `/v1/decide` を一度だけ呼び、実際の response を返します。
`candidate_factory(action, pre_state, rcc_review)` は型付きの提案を native
DecisionCandidate に写像します。提案をユーザーの元の要求へコピーしないでください。
`request_context` は元の要求と実行時に利用可能な情報だけを返します。

`verify_receipt(response)` は実際に保存された TrustLog と replay のハッシュ・
識別子・lineage を検証し、検証できた場合だけ bool の True を返します。
単なる echo の一致では不十分です。RCC hash を VERITAS canonical hash として
再命名せず、native CDA と promotion から生成された値を使用します。
response と CDA の判断が矛盾する場合も実行されません。

native 保存を検証する場合は `append_native_trustlog=True` と
`native_trustlog_verifier(receipt, intent)` を指定してください。
実行後の保存確認に失敗しても、「効果なし」とは記録しません。
実際に callback を実行する主体は NativeBindExecutor 一つだけです。

権限、policy、scope、失効情報は agent とは独立した source から解決してください。
Human Approval が不要なのは確認済みの policy/action contract がそう定義している
場合だけです。不足した approval を作って通すことはしません。

## 複数ベンチマーク

`rveval matrix` は、全 configuration を登録し、全 freeze を完了・再検証してから
最初の実行に進みます。一つでも準備に失敗すれば、その段階ではどれも実行しません。
各 benchmark は新しいプロセスで実行するため、前の scorer のグローバル状態を
次の benchmark に持ち込みません。途中で設定が変わっても再 freeze はしません。
元の scorer と集計方法を維持し、失敗・未対応・欠落を分母から黙って消しません。

AgentDojo、lm-eval、Gymnasium、Inspect、tau 系、SWE-bench の具体的な binding と、
その他の native API / 永続 RPC 用契約は英語版と既存の API 文書にあります。
新しい task が同じ native API を使う場合は binding を再利用できます。
まったく別の API は、意味を保つ adapter と conformance test が必要です。

## SWE-bench

swebench 5.0.2 と古い dataset schema の組合せでは image 欠落で失敗しました。
公式 v5 schema に合わせた後、実際の Docker grading が完了しています。
これは既知の gold patch を使った環境確認であり、モデル性能の証明ではありません。

実際の提出用 patch は、次のコマンドで公式 grader に渡せます。

```
python scripts/run_swe_native.py --dataset-json /data/exact-official-records.json --predictions /data/sealed-predictions.jsonl --output /results/swe-new --run-id unique-frozen-run --workers 1
```

dataset-json は **scorer 専用**です。tests/reference patch を agent や gate に渡さないでください。
公式 schema、登録件数、prediction の対応関係を確認してから実行します。
全問題を解けなくても grading 自体は正常完了し得ます。未実行・重複・環境失敗と、
モデルの不正解を区別します。Docker と必要 image は実行環境に用意してください。

返却時には exact pins、freeze、provider 設定、native outputs、全 error、
CDA/promotion/BindReceipt、実際の永続化検証、公式 score をまとめてください。
固定 provider、replay、live 実行の区別を残したまま、共同の成績実験へ進めます。
