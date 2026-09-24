# Takeshiさん向け実装手順 v0.3.3

今回の入口は `TAKESHI_IMPLEMENTATION_v0.3.3.md` と
`contracts/VERITAS_MAPPING_v0.3.3.json` です。初期 mapping の Q1〜Q9 に対する回答、
12 項目の入出力・責任・欠落時の扱い、実装済み関数への参照をまとめました。
古い版のレポートは履歴であり、現在の対応状況ではありません。

## 既存 benchmark のループを変更せずに接続する

`reset/step` 型は従来の Adapter/Session を使用します。既存 Python SDK は
`NativeGovernanceHook` と `NativeBindExecutor`、非同期 SDK は
`AsyncNativeBindExecutor` に接続します。ループ全体を持つ外部コマンド、別言語、
コンテナには新しい **native-job/v1** を使用してください。同じ CLI の
check / freeze / run / verify / matrix から実行できます。

native-job は execute と score の2段階です。execute の入力には公開ランタイム入力のみを
渡します。全登録ケースの A/B 実行記録を固定してから、別プロセスで元の採点器を呼びます。
独自の平均正解率へ変換せず、公式の集計結果をそのままファイルとして残します。
不明・例外・未対応・タイムアウトを正常な拒否や欠落した分母として扱いません。
自動再試行はしません。既存出力ディレクトリの再利用も拒否します。

`examples/native_job/worker.py` は疑似コードではなく、行列演算・ストリーム処理・
非同期 fan-in・バイナリ信号演算を実行する例です。これは接続確認のための同一 A/B
対照で、VERITAS を呼んだと偽るものではありません。実際の VERITAS の全 native 経路は
`examples/native_decide_bind/sandbox.py` を使用してください。

```bash
export PYTHONPATH="$PWD/src"
python -m rveval mapping-check --contract contracts/VERITAS_MAPPING_v0.3.3.json
python -m rveval freeze --config examples/native_job/config.json --output /tmp/new-native.freeze.json
ACK=$(python -m rveval hash /tmp/new-native.freeze.json)
python -m rveval run --config examples/native_job/config.json \
  --freeze /tmp/new-native.freeze.json --ack-freeze-sha256 "$ACK" --output-dir /tmp/new-native-result
INDEX=$(python -m rveval hash /tmp/new-native-result/evidence_index.json)
python -m rveval verify --run-dir /tmp/new-native-result --expected-index-sha256 "$INDEX"
```

## Mapping の固定内容

`build_runtime_packet()` は実際の CandidateAction、ADOPT 済み RCCDecision、候補とは
独立した元の request、元資料の参照と hash、タイムゾーン付き生成時刻を受け取ります。
`verify_runtime_packet()` が選択候補・採用結果・各 hash の整合性を検査します。
パケットは `rveval.veritas-input.v1` であり、VERITAS CDA/BindReceipt ではありません。
packet_created_at はパケット生成時刻で、過去の意思決定時刻を創作するものではありません。
ネイティブ decision_id/hash/ts は既存 VERITAS が発行し、既存検証器が検証します。

元の Q1〜Q9 では、正規の downstream artifact、列挙値、hash と時刻、ID の相互関係、
execution control、typed action、verifier provenance、NeoMundi の原資料参照、公開版と
非公開版の意味の境界を質問されていました。今回の JSON は各質問に対応する具体的な
回答と実装箇所を記載しています。公開版が非公開 RCC 全体と同じであるとは主張しません。

Actor/authority/policy/approval は独立した本来のソースから取得します。RCC の ADOPT、
候補本文、モデル名、正解ラベルで代用しません。Human Approval が必要な経路は本物の
ネイティブ証拠が必要です。NOT_REQUIRED は policy の判定で、receipt がないことと同義
ではありません。実際の外部効果を実行する主体は一つだけにしてください。

## Benchmark の妥当性と実装の動作は別です

SWE-bench Verified に関する2026年2月23日の公開監査では、採点上の欠陥と汚染が指摘され
ました。以前の正解パッチ Docker 実行はインストール確認としてのみ保存します。
それを汎用対応・frontier 能力・clean generalization の根拠にはしません。
他の benchmark へ変更しても、適切性・汚染・版・採点規則の確認は必要です。

native-job の実際の request、execution.json、scores.json の完全な形式は英語版にあります。
共通 CLI はファイル整合性、全ケース登録、順序、プロセス分離を検証しますが、任意の
外部プログラムの内部動作を独立に証明するものではありません。信頼できない workload は
ネイティブ benchmark のコンテナ/VM 内で動かしてください。

実装後は元の native scorer との一致、候補と状態の binding、実際の authority 検証と
単一実行、失敗記録を含む返却 packet を送ってください。新しい benchmark API には明示的な
wrapper が必要です。共通インターフェースがあることを、未実装 API まで既に動作したという
報告に変えないでください。
