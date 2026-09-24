# Takeshiさん向け実装手順 — v0.3.4

今回の修正はパイロットの可搬性です。旧版ではmappingを別ディレクトリへコピーすると
元のsource checkoutに依存して12項目が失敗しました。現在は実際にロードされている
rvevalパッケージのsourceとsymbolを検証し、そのhashを返します。

```bash
python -m pip install -e '.[test]'
python -m rveval init-pilot --name takeshi-next-pilot --output-dir ../takeshi-next-pilot
cd ../takeshi-next-pilot
python -m rveval mapping-check --contract contracts/mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-001
python -m rveval verify --run-dir run-001 \
  --expected-index-sha256 "$(python -m rveval hash run-001/evidence_index.json)"
```

wheelのインストール後も同じ手順で動作し、元のリポジトリの場所は不要です。
既存ディレクトリは上書きしません。生成物にはworker、実装用の2関数、実行入力と
採点専用入力、12フィールド群とQ1〜Q9、schema、native関数signature、英日説明が
含まれます。最初のA/Bは明示的な同一engineering controlであり、VERITASを実行した
とは記録しません。RCCの構造検証とruntime packetは実行します。

実際の接続では `pilot_impl.execute_case` を既存のtask/agent loopに、`score_run` を
本来のscorerに置き換えます。別言語や分散実行ではnative-job/v1のworker契約を
維持してください。新しいAPIにはadapterが必要ですが、共通runnerを再構築する
必要はありません。全実行の後に採点し、失敗・未対応・欠落を除外してPASSにはしません。

独立した依頼、候補、RCC adoption、native CDA、authority、approval、状態、BindReceipt
を分離してください。`NativeBindExecutor` の実行後に同じ操作を再実行しないでください。
細部は同梱の `TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md`、日本語版と
`NATIVE_API_SIGNATURES.md` にあります。このnative契約は変更していません。

未確認の権限、private RCC、未知のnative APIや未実行の全モデル実験が存在するかのような
記録は作りません。今回の検証範囲は `PUBLICATION_REVIEW.json` を参照してください。
