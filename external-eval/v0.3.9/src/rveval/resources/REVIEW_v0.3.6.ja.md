# v0.3.6 実装・再検証の追加事項

Takeshiさんに限らず、新しい実装者は `PARTNER_IMPLEMENTATION.md` から開始できます。
既存の12項目とQ1–Q9の意味、RCC AdoptionとVERITAS実行権限の境界は変更していません。

新しいstarterは、各case/armの**全trajectory**を独立したPython子プロセスで実行します。
Aが変更した入力やPythonのglobal stateがBへ漏れる問題を修正しました。ただし外部DB、
ファイル、provider session等は実装側の独立したsnapshot/resetが必要です。

`contracts/partner_bindings.json` に実際のsource/target、意味の責任者、変換、欠落時の扱い、
provenance、検証関数を記載してください。`partner-check` のPASSは記入と参照の検証であり、
実際のnative integrationや権限の正当性を証明するものではありません。
`templates/native_component_profile.json` もインストール先に同梱しました。

既知のRCC decision lockとhandoffの矛盾は、packetのhashを再計算しても通過できません。
source symbolは実際のmodule exportまたは `Class.method` である必要があります。
callbackはBindとrunnerで二重実行せず、失敗した効果はUNKNOWNとして保持してください。

元のnative scorer、governance、latency/cost/token/computeは別々に測定します。
このstarterのA/Bは同一のengineering controlであり、VERITASを実行したという主張ではありません。
