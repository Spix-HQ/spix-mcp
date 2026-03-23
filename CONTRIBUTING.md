# Contributing to Spix MCP

Thanks for your interest in contributing. This guide covers how to set up the dev environment, run tests, and submit a pull request.

## Before you start

- **Bug reports and feature requests**: open an issue first so we can discuss before you write code.
- **Small fixes** (typos, doc corrections, obvious bugs): PRs welcome without a prior issue.
- **Large changes**: open an issue first. We want to make sure the direction aligns before you invest the time.

## Development setup

Requirements: Python 3.10+, git.

```bash
git clone https://github.com/Spix-HQ/spix-mcp
cd spix-mcp

# Create a virtual environment
python3.10 -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Verify
spix-mcp --help
```

## Running tests

```bash
pytest
```

Run a specific test file or test:

```bash
pytest tests/test_tools.py
pytest tests/test_tools.py::test_call_create
```

Run with coverage:

```bash
pytest --cov=spix_mcp --cov-report=term-missing
```

All tests must pass before submitting a PR. If you're adding a feature, add tests for it.

## Code style

We use `ruff` for linting and formatting:

```bash
ruff check src/
ruff format src/
```

These run automatically in CI. Fix any issues before pushing.

## Commit messages

Use the conventional commits format:

```
feat: add spix_contact_merge tool
fix: handle timeout in call transcript retrieval
docs: clarify SPIX_API_KEY env var setup
test: add coverage for playbook voice list
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

Keep the subject line under 72 characters.

## Pull request checklist

- [ ] Tests pass: `pytest`
- [ ] Linting clean: `ruff check src/`
- [ ] New behavior is covered by tests
- [ ] PR description explains what changed and why

## What we don't accept

- Changes that break existing MCP tool schemas (downstream clients depend on them)
- New dependencies without discussion — we keep the dependency surface small
- Changes that expose destructive operations in the `safe` tool profile

## Questions?

Open a [GitHub Discussion](https://github.com/Spix-HQ/spix-mcp/discussions) or find us in the community.
