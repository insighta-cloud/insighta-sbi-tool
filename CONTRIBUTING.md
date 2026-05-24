# Contributing to insighta-sbi-tool

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Development Setup

### Requirements

- Python 3.10+
- pip
- `insighta-cli` (installed automatically as dependency)

### Installation

```bash
git clone https://github.com/insighta-cloud/insighta-sbi-tool.git
cd insighta-sbi-tool
pip install -e ".[dev]"
```

### Running

```bash
insighta --work sbi-us-stocks parse
insighta --work sbi-us-stocks verify
```

## Code Style

- Follow PEP 8
- All comments and docstrings in English
- Type hints required for public APIs
- Use `beautifulsoup4` for HTML parsing, `pandas` for CSV parsing

## Adding Support for New SBI File Formats

1. Add a classifier rule in `parser_v2.py` → `classify()`
2. Implement a parser function returning `ParseResult`
3. Register it in `_HANDLERS`
4. Add test fixtures (anonymized HTML/CSV samples)

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: support new deposit CSV format
fix: handle edge case in history HTML parsing
test: add fixture for currency exchange CSV
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests with fixture data
4. Ensure `insighta parse` and `insighta verify` work correctly
5. Submit a pull request against `main`

## Test Fixtures

Place anonymized test data in `tests/fixtures/`:
- HTML files: remove personal information, keep structure
- CSV files: use dummy tickers and amounts

## Multilingual Support (i18n)

CLI output messages for SBI-specific commands should be added to the i18n system in `insighta-cli`. Coordinate with the CLI package when adding new user-facing strings.

Source code (comments, docstrings, variable names) must be in English.

## License

By contributing, you agree that your contributions will be licensed under the CC-BY-NC-4.0 license.
