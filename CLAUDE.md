# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Activate virtual environment: `source .venv/bin/activate`
- Install build dependencies: `uv pip install setuptools wheel build'`
- Build: `python -m build`
- Install test dependencies: `uv pip install -e '.[test]'`
- Test: `pytest`
- Lint: `just lint` (runs black, cog, mypy, ruff)
- Type check: `just mypy`
- Auto-format: `just fix` (ruff --fix + black)

## Code Style
- Line length: 160 chars (ruff.toml)
- Type hints: Use throughout, import from typing (List, Dict, Optional, etc.)
- Imports: Standard lib first, third-party second, local modules last
- Classes: Use dataclasses and Pydantic models with type annotations
- Error handling: Custom exceptions in errors.py
- Documentation: Use docstrings, maintain docs with cog
- Testing: pytest with fixtures, parametrized tests
- Async: Use async/await pattern where needed (asyncio_default_fixture_loop_scope = function)

## Python Requirements
- Python 3.9+
- Black 25.1.0+ for formatting
- Mypy for type checking (see mypy.ini for ignored imports)