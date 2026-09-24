# Takeshiさん向け: 0.3.0 native実装・実行案内

今回は抽象的なadapterの仕様だけでなく、実際の外部ライブラリに接続するコードを追加しています。
英語版 `NATIVE_IMPLEMENTATION_v0.3.md` が引数・返却値を含む正本です。

## 最初に実行するもの

Linux x86-64 / Python 3.13 / Git / Nodeを基準に、`bash scripts/bootstrap_native.sh`。
続いて表示される `scripts/validate_native.py` のコマンドを実行してください。
既存の出力ディレクトリは再利用しません。依存関係が欠けたりテストがskipされた場合はPASSにしません。

## 今回の具体的な変更

`ExternalRCCGate` は外部候補を受ける新しいpolicy-boundの検証・採用・decision-lock実装です。
古いsynthetic-only releaseを変更していません。公開output contractの検査だけで回答の正しさを証明したとは扱いません。
`CanonicalRCCGate` は古い実行可能RCCの本物の関数を、元の範囲を保持して呼び出します。

`NativeBindExecutor` はVERITASの本物の `execute_bind_adjudication` を呼び出します。
権限・制約・risk・postconditionのcallbackとnative ExecutionIntentは、実際の対象から解決してください。
候補からユーザーの依頼や権限を逆算して作ってはいけません。
署名付きAuthorityEvidenceには `NativeAuthorityResolver` を用意しました。
正常署名・改ざん・失効をnative verifierとBindまで通す実行テストもあります。

## 接続点

AgentDojoは `make_runtime_class`。workspace/travel/banking/slackで同じコードを使用します。
既存のBanking固有task policyを他のsuiteへコピーしません。
lm-evalは `make_lm` で生成・loglikelihood・rollingを保持します。
Gymnasiumは `make_env` で元のstep/reset/reward/terminationを保持します。
Inspectは `govern_tool`、asyncな本物のBindには `AsyncNativeBindExecutor` を使います。
SWE-benchは `PredictionWriter` と公式harnessのコマンドを使います。
tau-benchは `LegacyTauEnv`、tau2/tau3は `TauToolBinding` です。
その他はsync/async native call境界または既存の永続RPCに接続できます。

## 再発させてはいけない点

タスクのgold、oracle actions、native scorerの返却内容をgovernorへ渡さないこと。
特に旧tauのreward関数はoracle actionを再生します。そこをagent操作として計測しない実装になっています。
AgentDojoのファイル・メール作成はwall clockを使うため、同一状態比較では双方の時計条件を固定する必要があります。
タイムスタンプを削除して同じ結果に見せるのではなく、外生的入力を先に固定します。

async呼び出しの待機側がcancelされても、開始済みのeffectを自動再実行しません。
終了時には `await async_executor.drain()` でreceiptを回収します。
`OperationLedger` は同じoperation IDのローカル重複試行を防ぎますが、分散exactly-onceの保証ではありません。

## 評価結果の境界

native接続テストのPASSは、選択した接続と範囲で実行した証拠です。
全公開benchmarkの全タスクや、API keyを使うfrontier model実験を実行したという意味ではありません。
全trajectoryのtask scoreと同一候補counterfactualを分け、block数をattack防御数に変換しません。

旧版と失敗履歴を保持し、今回のnativeコード・policy・benchmark・モデル・scorerをexact pinで指定して進めてください。
