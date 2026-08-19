# Contributing to accessipdf

Thank you for your interest in improving accessipdf! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- **Python**: 3.12 or newer
- **veraPDF CLI**: Required for PDF/UA-1 validation
  - **macOS**: `brew install verapdf`
  - **Linux (Debian/Ubuntu)**: `sudo apt-get install verapdf`
  - **Windows**: Download from [veraPDF releases](https://github.com/veraPDF/veraPDF-apps/releases)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/mkupermann/accessipdf.git
cd accessipdf

# Create virtual environment and install dependencies
python -m venv .venv
.venv/bin/pip install -e '.[dev]'

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# Run the demo
.venv/bin/python -m accessipdf.demo demo_invoice.pdf

# Run tests
.venv/bin/pytest -q
```

## Running Tests

The full test suite validates:
- PDF/UA-1 compliance via veraPDF
- Pixel-perfect rendering
- Text extraction integrity

```bash
# Run all tests
.venv/bin/pytest

# Run with coverage
.venv/bin/pytest --cov=accessipdf --cov-report=term

# Run specific test
.venv/bin/pytest tests/test_golden.py -v
```

## Adding a New Layout Template

accessipdf uses YAML templates to define PDF layouts. To add support for a new layout:

1. **Analyze the PDF**: Use the zone dump script to find text coordinates:
   ```bash
   .venv/bin/python scripts/zonen_dump.py your_file.pdf 1
   ```

2. **Create a template file**: Add a new `.yaml` file in `accessipdf/templates/vorlagen/`

3. **Define anchors**: Identify unique text that appears in the same location across all documents of this layout

4. **Define zones**: Map bounding boxes to semantic roles (H1, P, Table, Artifact, etc.)

5. **Test**: Run the pipeline with your PDF:
   ```bash
   .venv/bin/accessipdf identify your_file.pdf
   .venv/bin/accessipdf convert your_file.pdf ausgang/
   ```

See `accessipdf/templates/vorlagen/acme-demo.yaml` for a reference template.

## Code Quality

### Type Checking

```bash
.venv/bin/mypy accessipdf/
```

### Linting

```bash
# Using ruff (recommended)
ruff check accessipdf/ tests/ scripts/
ruff format accessipdf/ tests/ scripts/
```

### Pre-commit

The project uses pre-commit hooks for automated quality checks:

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Project Structure

```
accessipdf/
├── accessipdf/
│   ├── __init__.py          # Package metadata and version
│   ├── cli.py               # Command-line interface
│   ├── demo.py              # Synthetic demo invoice generator
│   ├── pipeline.py          # Main conversion pipeline
│   ├── semantics.py         # Semantic role assignment
│   ├── testkit.py           # Test utilities
│   ├── core/
│   │   └── model.py         # Core data models
│   ├── tagging/
│   │   ├── __init__.py
│   │   ├── fonts.py         # Font repair utilities
│   │   ├── metadata.py      # PDF metadata handling
│   │   ├── structure.py     # Structure tree building
│   │   ├── tables.py        # Table handling
│   │   ├── tokenizer.py     # Text tokenization
│   │   ├── walker.py        # PDF content walking
│   │   └── wrap.py          # Content stream wrapping
│   ├── templates/
│   │   ├── __init__.py
│   │   └── loader.py        # Template loading and layout identification
│   │   └── vorlagen/        # Layout template YAML files
│   └── validate/
│       ├── __init__.py
│       └── verapdf.py       # veraPDF validation wrapper
├── scripts/
│   └── zonen_dump.py        # Zone coordinate extraction utility
├── tests/
│   └── *.py                 # Test suite
├── docs/
│   └── media/               # Demo media files
├── .github/
│   └── workflows/
│       └── test.yml         # CI configuration
├── .pre-commit-config.yaml # Pre-commit hooks
├── pyproject.toml          # Project configuration
├── README.md               # Project documentation
└── LICENSE                 # MIT License
```

## Reporting Issues

When reporting issues, please include:
- Python version
- Operating system
- veraPDF version (`verapdf --version`)
- Steps to reproduce
- Sample PDF (if possible, anonymized)

## Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure all tests pass
5. Run pre-commit hooks
6. Add tests for new functionality
7. Update documentation as needed
8. Submit the pull request

All pull requests will be reviewed and may require additional changes before merging.

## License

By contributing to this project, you agree to license your contributions under the MIT License. See [LICENSE](LICENSE) for details.
