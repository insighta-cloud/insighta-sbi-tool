# insighta-sbi-tool

[![CI](https://github.com/insighta-cloud/insighta-sbi-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/insighta-cloud/insighta-sbi-tool/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/insighta-sbi-tool)](https://pypi.org/project/insighta-sbi-tool/)
[![Python](https://img.shields.io/pypi/pyversions/insighta-sbi-tool)](https://pypi.org/project/insighta-sbi-tool/)
[![License](https://img.shields.io/badge/license-CC--BY--NC--4.0-blue)](LICENSE)

[insighta-cli](https://github.com/insighta-cloud/insighta-cli) 用の SBI証券パーサープラグイン。

## インストール

```bash
pip install insighta-sbi-tool
```

`insighta-cli` と `insighta-sdk` が依存関係として自動インストールされます。

## 使い方

```bash
# SBI取引履歴をCSVにパース
insighta --work sbi-us-stocks parse

# パース結果を現在の保有銘柄と照合
insighta --work sbi-us-stocks verify
```

## 認証

[insighta.cloud/settings](https://insighta.cloud/settings) の **Developer** タブから API キーを取得し、保存します：

```bash
insighta config --credentials credentials.yaml
```

`credentials.yaml` の形式：

```yaml
api_key: "your-api-key-here"
endpoint: "https://openapi.insighta.cloud"
```

## 対応フォーマット

| 種類 | 形式 | エンコーディング |
|------|------|-----------------|
| 注文履歴 | HTML (Webスクレイプ) | UTF-8 |
| 保有銘柄一覧 | HTML (Webスクレイプ) | UTF-8 |
| 約定履歴 | CSV | Shift_JIS |
| 入出金振替 | CSV | UTF-8 |
| 外貨入出金 | CSV | UTF-8 |
| 為替取引 | CSV | Shift_JIS |
| 配当金 | CSV | Shift_JIS |
| 国内投信取引 | CSV | Shift_JIS |

## ワークスペース構成

```
workspaces/sbi-us-stocks/
├── input/
│   ├── sbi/          ← SBIファイルをここに配置（自動分類）
│   ├── seed/         ← 既存保有銘柄CSV（任意）
│   └── rate.csv      ← 為替レート期間（任意）
└── output/
    ├── history.csv   ← 生成された取引履歴
    ├── order.csv     ← 生成された注文グループ
    └── upload.yaml   ← アップロード設定
```

## 開発

```bash
pip install -e .
insighta --help
```

ガイドラインは [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## ライセンス

CC-BY-NC-4.0 — [LICENSE](LICENSE) を参照
