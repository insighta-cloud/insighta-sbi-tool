# insighta-sbi-tool

SBI Securities (Japan) parser plugin for [insighta-cli](https://github.com/insighta-cloud/insighta-cli).

## Installation

```bash
pip install insighta-sbi-tool
```

This automatically installs `insighta-cli` and `insighta-sdk` as dependencies.

## Usage

```bash
# Parse SBI trade history into CSV
insighta --work sbi-us-stocks parse

# Verify parsed data against current holdings
insighta --work sbi-us-stocks verify
```

## Supported Formats

| Type | Format | Encoding |
|------|--------|----------|
| Order history | HTML (web scrape) | UTF-8 |
| Holdings summary | HTML (web scrape) | UTF-8 |
| Trade settlement | CSV | Shift_JIS |
| Transfer history | CSV | UTF-8 |
| Foreign currency deposits | CSV | UTF-8 |
| Currency exchange | CSV | Shift_JIS |
| Dividends | CSV | Shift_JIS |
| Domestic fund trades | CSV | Shift_JIS |

## Workspace Structure

```
workspaces/sbi-us-stocks/
├── input/
│   ├── sbi/          ← Place all SBI files here (auto-classified)
│   ├── seed/         ← Pre-existing holdings CSV (optional)
│   └── rate.csv      ← Exchange rate periods (optional)
└── output/
    ├── history.csv   ← Generated trade history
    ├── order.csv     ← Generated order groups
    └── upload.yaml   ← Upload configuration
```

## Development

```bash
pip install -e .
insighta --help
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

CC-BY-NC-4.0 — See [LICENSE](LICENSE)
