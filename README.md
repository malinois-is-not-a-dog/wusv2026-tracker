# WUSV 2026 Tracker

スマホで見やすい WUSV World Championship IP 2026 の出場選手・成績・スケジュールのページです。英語と日本語を切り替えられます。

- 公開ページ: GitHub Pages（このリポジトリの Settings → Pages）
- データ: `data.json` は GitHub Actions（`.github/workflows/update.yml`）が公式 fci.systems から自動で取得します
  - 大会期間（10/5〜10/12）は5分おき、それ以外は6時間おき
  - Actions タブ → Update results → Run workflow で、すぐに手動更新できます
- ページは開いている間、1分ごとに `data.json` を読み直します

## 編集
`src/app.html`・`src/*.css` を編集してから `python3 scripts/build.py` を実行すると `index.html` ができます。

## 順位ルール
総合点の高い順。同点ならC科目の高い方、さらに同点ならB、Aの順に比べます。
