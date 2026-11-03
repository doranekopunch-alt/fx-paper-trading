# FX仮想1万円・自動記録

## セットアップ（初回のみ）
1. GitHubで新規リポジトリを作成し、このZIPを展開したファイルをアップロードする。
2. リポジトリ Settings → Actions → General → Workflow permissions を **Read and write permissions** にする。
3. Actions タブで `FX daily paper trading` を `Run workflow` で初回実行する。
4. Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/docs` → Save。
5. 表示された Pages URL をAndroidのChromeで開く。

**注意** GitHub Pagesは原則公開URLです。個人情報や口座情報は置かないでください。
公開したくない場合は、公開前に別の認証付きホスティングへ切り替えてください。
GitHub Actionsの定期実行は遅延・スキップがあり、無料枠・利用規約・リポジトリの休眠停止条件が変わることがあります。
毎日確実に実行されることは保証されません。

## 設計
- USDJPY/EURJPY/EURUSD、2年の日足、20/60日移動平均。
- 仮想資金10,000円を3通貨へ等分。1倍の仮想エクスポージャー。
- 初回実行日から記録開始。過去のバックテスト損益を仮想残高へ足さない。
- 同じ日付は重複計上しない。データ欠落・エラーは表示する。
- 実際のFX取引はしない。実際の証拠金や強制ロスカットのモデルではない。
- Yahoo Financeのデータは遅延・欠損・訂正される可能性がある。
- コストは簡易近似であり、スワップ・税金・スリッページ等は未反映。
- 毎朝08:20 JSTの実行を要求するが、GitHub Actionsがその時刻に実行する保証はない。
