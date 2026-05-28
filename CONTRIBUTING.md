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
pre-commit install
```

### Running

```bash
insighta --work sbi-us-stocks parse
insighta --work sbi-us-stocks verify
```

## Code Style

- Follow PEP 8 (enforced by Ruff)
- All comments and docstrings in English
- Type hints required for public APIs
- Use `beautifulsoup4` for HTML parsing, `pandas` for CSV parsing
- Line length limit: 120 characters

### Docstrings

Use [Google-style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) docstrings:

- **Click command functions**: One-line summary only (click uses it as `--help` text).
- **Utility / internal functions**: Full Google-style with `Args`, `Returns`, `Raises` as needed.

### Linting & Formatting

```bash
ruff check insighta_sbi/       # lint
ruff check insighta_sbi/ --fix # auto-fix
ruff format insighta_sbi/      # format
```

### Pre-commit Hooks

```bash
pre-commit install
```

### Testing

```bash
pytest tests/ -x -q
```

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

## Releasing to PyPI

When publishing a new version:

1. Bump `version` in `pyproject.toml`
2. Commit the version bump (`chore: bump version to X.Y.Z`)
3. Tag the commit (`git tag vX.Y.Z`)
4. Push the commit **and** tag (`git push origin main --tags`)
5. Build and upload:
   ```bash
   python -m build
   python -m twine upload dist/insighta_sbi_tool-X.Y.Z*
   ```

**The version bump commit must be pushed before uploading to PyPI.** The Git tag and PyPI version must always match.

## License

By contributing, you agree that your contributions will be licensed under the CC-BY-NC-4.0 license.
