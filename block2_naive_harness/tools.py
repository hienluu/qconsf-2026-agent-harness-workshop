"""Local tools for the naive harness.

Every tool operates inside one task workspace directory. Path traversal is
blocked (the one safety feature even a naive harness must have), but that is
the ONLY guardrail here: no output truncation, no timeouts beyond pytest's,
no permissions. Those omissions are the point — Block 3 adds them and
measures the difference.
"""

import subprocess
import sys
from pathlib import Path


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def _path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError(f"path escapes workspace: {rel}")
        return p

    def list_files(self) -> str:
        """Relative paths of every file in the workspace."""
        files = [
            str(p.relative_to(self.root))
            for p in sorted(self.root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts
        ]
        return "\n".join(files)

    def read_file(self, path: str) -> str:
        return self._path(path).read_text()

    def write_file(self, path: str, content: str) -> str:
        target = self._path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return f"wrote {len(content)} chars to {path}"

    def search(self, pattern: str) -> str:
        """Every line in the workspace matching a literal substring."""
        hits = []
        for p in sorted(self.root.rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            for i, line in enumerate(p.read_text().splitlines(), 1):
                if pattern in line:
                    hits.append(f"{p.relative_to(self.root)}:{i}: {line}")
        return "\n".join(hits) or f"no matches for {pattern!r}"

    def run_tests(self) -> str:
        """Run pytest in the workspace and return its FULL output, untruncated."""
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=long", "-q"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return proc.stdout + proc.stderr


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List every file in the workspace as relative paths.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read one file. Path is relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite one file with new content. Path is relative to the workspace root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Find every line containing a literal substring, across all .py files.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the workspace test suite with pytest. Success means exit green.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
