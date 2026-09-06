"""fix_bug through Pydantic AI.

    uv run --group block4 pydantic_ai/run.py         (from block4_production_harnesses/)

Pedigree: composable à la carte — a lean typed core, with harness behavior
assembled from capabilities you opt into rather than a bundle you accept.
Notice the provider portability: this is the only Block 4 harness with no
home vendor at all — the model is just a parameter. And notice the typed
tools: signatures + docstrings become the schema; a wrong type is a
retryable validation error, not a runtime surprise.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TASK, prepare_workspace, verify  # noqa: E402

from pydantic_ai import Agent  # noqa: E402
from pydantic_ai.models.openai import OpenAIChatModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402

load_dotenv()
NAME = "pydantic_ai"
workspace: Path

# Provider-portable by construction: any OpenAI-compatible endpoint is a
# constructor argument, not an environment contract.
model = OpenAIChatModel(
    os.environ["MODEL"],
    provider=OpenAIProvider(
        base_url=os.environ["PROVIDER_BASE_URL"],
        api_key=os.environ["PROVIDER_API_KEY"],
    ),
)

agent = Agent(
    model,
    instructions=(
        "You fix bugs in a small Python workspace using the provided tools. "
        "The task is complete only when run_tests reports every test passing."
    ),
)


@agent.tool_plain
def read_file(path: str) -> str:
    """Read one file, path relative to the workspace."""
    return (workspace / path).read_text()


@agent.tool_plain
def write_file(path: str, content: str) -> str:
    """Overwrite one file, path relative to the workspace."""
    (workspace / path).write_text(content)
    return f"wrote {len(content)} chars"


@agent.tool_plain
def run_tests() -> str:
    """Run pytest in the workspace; done means all tests pass."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace, capture_output=True, text=True, timeout=120,
    )
    return proc.stdout + proc.stderr


def main() -> int:
    global workspace
    workspace = prepare_workspace(NAME)
    started = time.monotonic()
    result = agent.run_sync(TASK)
    print(f"[{NAME}] final: {str(result.output)[:100]}")
    print(f"[{NAME}] usage: {result.usage}")
    return verify(NAME, workspace, started)


if __name__ == "__main__":
    raise SystemExit(main())
