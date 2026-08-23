# Contributing

Contributions are welcome. For major changes, open an issue first to discuss
what you would like to change.

## Development Setup

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/MichailSemoglou/color-analysis-tool.git
   cd color-analysis-tool
   ```

2. Create a virtual environment and install the development dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. Run the checks CI enforces before committing:

   ```bash
   pytest                                               # tests with coverage
   flake8 color_analysis_tool/ --max-line-length=120    # lint
   mypy color_analysis_tool/                            # type check
   isort --check color_analysis_tool/ tests/            # import order
   pip-audit                                            # dependency audit
   ```

The test suite builds synthetic in-memory images, so no fixture files are
needed. New behavior needs new tests, and CI fails below 90% coverage.

## Pull Requests

- Open one pull request per logical change, with a short description of
  what changed and why.
- Add or update tests for any behavior change. CI runs on every pull
  request and must pass.
- The maintainer takes care of changelog entries, versioning, and release
  notes.

## Reporting Issues

Bug reports and feature requests go to GitHub Issues. Report security
vulnerabilities through the private channel in `SECURITY.md`, never in a
public issue.
