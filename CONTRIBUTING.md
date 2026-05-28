# insighta-sbi-tool への貢献

コントリビュートに興味を持っていただきありがとうございます。このドキュメントはプロジェクトへの貢献ガイドラインです。

## 開発環境セットアップ

### 必要条件

- Python 3.10+
- pip
- `insighta-cli`（依存関係として自動インストール）

### インストール

```bash
git clone https://github.com/insighta-cloud/insighta-sbi-tool.git
cd insighta-sbi-tool
pip install -e ".[dev]"
pre-commit install
```

### 実行

```bash
insighta --work sbi-us-stocks parse
insighta --work sbi-us-stocks verify
```

## コードスタイル

- PEP 8 準拠（Ruff で強制）
- コメント・docstring はすべて日本語
- 公開 API には型ヒント必須
- HTML パースには `beautifulsoup4`、CSV パースには `pandas` を使用
- 行長制限：120文字

### Docstring

[Google スタイル](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) の docstring を使用：

- **Click コマンド関数**：1行の要約のみ（`--help` テキストとして使用される）。
- **ユーティリティ / 内部関数**：`Args`、`Returns`、`Raises` を含む完全な Google スタイル。

### リント＆フォーマット

```bash
ruff check insighta_sbi/       # リント
ruff check insighta_sbi/ --fix # 自動修正
ruff format insighta_sbi/      # フォーマット
```

### Pre-commit フック

```bash
pre-commit install
```

### テスト

```bash
pytest tests/ -x -q

# ライブテスト（API接続あり）
INSIGHTA_DEV_API_KEY=your-key pytest --live
```

## 新しい SBI ファイル形式の追加

1. `parser_v2.py` の `classify()` に分類ルールを追加
2. `ParseResult` を返すパーサー関数を実装
3. `_HANDLERS` に登録
4. テストフィクスチャを追加（匿名化した HTML/CSV サンプル）

## コミットメッセージ

[Conventional Commits](https://www.conventionalcommits.org/) を使用：

```
feat: 新しい入出金CSVフォーマットに対応
fix: 注文履歴HTMLのエッジケースを修正
test: 為替取引CSVのフィクスチャを追加
```

## プルリクエスト

1. リポジトリをフォーク
2. フィーチャーブランチを作成（`git checkout -b feat/my-feature`）
3. フィクスチャデータを使ったテストを作成
4. `insighta parse` と `insighta verify` が正常に動作することを確認
5. `main` に対してプルリクエストを送信

## テストフィクスチャ

匿名化したテストデータを `tests/fixtures/` に配置：
- HTML ファイル：個人情報を削除し、構造を維持
- CSV ファイル：ダミーのティッカーと金額を使用

## PyPI へのリリース

新バージョンを公開する場合：

1. `pyproject.toml` の `version` を更新
2. バージョンバンプをコミット（`chore: bump version to X.Y.Z`）
3. コミットにタグを付与（`git tag vX.Y.Z`）
4. コミットとタグをプッシュ（`git push origin main --tags`）
5. ビルド＆アップロード：
   ```bash
   python -m build
   python -m twine upload dist/insighta_sbi_tool-X.Y.Z*
   ```

**PyPI にアップロードする前に、バージョンバンプのコミットをプッシュすること。** Git タグと PyPI バージョンは常に一致させる。

## ライセンス

コントリビュートすることにより、あなたの貢献が CC-BY-NC-4.0 ライセンスの下でライセンスされることに同意したものとみなされます。
