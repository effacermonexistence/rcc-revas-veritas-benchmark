# v0.3.4 実装開始ガイド

今回は、インストール済みパッケージだけで独立したPilot作業ディレクトリを
作成できます。RCC判定ポリシーの空の検証リストと、メモリ内ポリシーの変更を
見逃す問題も修正しました。従来のsource pinや実験結果は変更していません。

```bash
python -m rveval init-pilot --pilot-id takeshi-pilot --output-dir ../takeshi-pilot
cd ../takeshi-pilot
python -m rveval mapping-check --contract mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-new
python -m rveval verify --run-dir run-new --expected-index-sha256 "$(python -m rveval hash run-new/evidence_index.json)"
```

生成されたSTART_HERE.mdに実装手順があります。worker.pyのexecute側を実際の
benchmark/agent/native VERITAS呼出しに、score側を元の公式scorerに置き換えます。
付属のworkerは明示的なengineering controlです。これをVERITAS treatmentや
新しい外部benchmarkの実装完了と呼ばないでください。

12項目のmappingとQ1–Q9はTAKESHI_IMPLEMENTATION_v0.3.3.ja.md、native callbackの
具体的な責務はTAKESHI_FINAL_IMPLEMENTATION_v0.3.2.ja.mdにあります。
今回のportable mappingはインストールされたrveval moduleの正確なhashとsymbolを
確認します。ソースcheckoutのディレクトリ構造には依存しません。

元のユーザー要求とcandidateを別々に取得してください。RCCのADOPTはAuthorityや
Human Approvalを発行しません。実際のeffect ownerは一つだけです。候補、状態、
policy、authority、scorer、モデルとbudgetを固定し、unknown/deny/error/timeout/
tamper/duplicateのcontrolも実行してから、本番の評価用pinを決めてください。

未知のnative APIにはadapterが必要ですが、共通実行・採点coreを作り直す必要は
ありません。新規Pilotでも、元のscheduler、tool semantics、scorerを保持します。
