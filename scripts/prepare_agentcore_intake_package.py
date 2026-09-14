"""Build a generated, narrow CodeZip context from canonical Relay source.

The output directory (``agentcore-runtime/RelayIntake/build/``) is gitignored and
is regenerated deterministically from the files listed below. It contains only
the modules the Intake Agent needs: no database, API, tool, or MCP code.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "agentcore-runtime" / "RelayIntake" / "build"
FILES = (
    "agentcore_runtime.py",
    "app/__init__.py",
    "app/agents/__init__.py",
    "app/agents/factory.py",
    "app/agents/model.py",
    "app/agents/prompts/__init__.py",
    "app/agents/prompts/intake.py",
    "app/agents/prompts/coordination.py",
    "app/agents/prompts/exception.py",
    "app/core/__init__.py",
    "app/core/config.py",
    "app/core/errors.py",
    "app/domain/__init__.py",
    "app/domain/base.py",
    "app/domain/agents.py",
    "app/domain/enums.py",
    "app/observability/__init__.py",
    "app/observability/agents.py",
    "app/schemas/__init__.py",
    "app/schemas/intake.py",
    "app/schemas/agentcore.py",
    "app/services/__init__.py",
    "app/services/intake.py",
    "app/services/agentcore_intake.py",
)
# The dependency line below is kept byte-identical to the deployed build manifest.
PYPROJECT = (
    """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "relay-agentcore-intake"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
"""
    + ' "awscrt==0.36.3", "bedrock-agentcore==1.23.0", "pydantic>=2.10,<3",'
    + ' "pydantic-settings>=2.10.1,<3", "strands-agents==1.55.1"\n'
    + """]

[tool.hatch.build.targets.wheel]
packages = ["app"]
"""
)


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    for relative in FILES:
        source = ROOT / "backend" / relative
        if not source.is_file():
            raise FileNotFoundError(source)
        target = BUILD / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (BUILD / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    files = (path for path in BUILD.rglob("*") if path.is_file())
    print("\n".join(sorted(path.relative_to(BUILD).as_posix() for path in files)))


if __name__ == "__main__":
    main()
