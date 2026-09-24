# 新しいパイロットを開始する手順

このディレクトリは元のリポジトリの場所に依存しません。配布した wheel を
インストールし、まず `START_HERE.md` の4つのコマンドをそのまま実行してください。
マッピング検証、freeze、A/B実行、証拠検証まで再現できます。

最初のサンプルのA/Bは**同一の工学的コントロール**です。RCCの構造検証と
packetは実行しますが、VERITASを実行したとは記録しません。

実際のパイロットでは `pilot_impl.py` の `execute_case` を既存のエージェント／
ベンチマークのループに、`score_run` をそのベンチマーク本来の採点器に置き換えます。
実行入力は `cases.json`、採点専用入力は `targets.json` です。全件・全armの
実行後にのみ採点プロセスを開始します。必要ならworker自体を別言語の実行器に
置き換えても、native-job/v1の入出力契約と共通runnerは変わりません。

元の依頼と提案candidateを別の出所から保持してください。Bでは既存のVERITAS
native pipelineと、独立したauthority・policy・approval・live-stateを使用します。
`NativeBindExecutor` が一度実行した操作をもう一度実行しないでください。
欠けた権限やHuman Approvalを作り出してPASSにしてはいけません。

`contracts/mapping.json` は12フィールド群とQ1〜Q9を含みます。
`mapping-check` はインストール済みrvevalの実ファイルとsymbolを確認します。
権限、状態、receipt、関数signatureの詳細は `docs/` に同梱しています。
新しいコード・データ・モデル・policy・scorerを設定した後、必ず新しいfreezeと
新しいoutputにしてください。ERROR、UNSUPPORTED、未完了を除外して分母を
小さくすることはありません。正答率が0でも正常完了になり得ますが、実行エラーを
正常な拒否として扱うことはありません。
