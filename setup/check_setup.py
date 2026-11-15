"""Pre-workshop setup check. Run this at home, on real WiFi.

    uv run setup/check_setup.py

Expected final line: ALL GREEN. Anything else: follow the hints, or bring
the output to the workshop help desk (before 9am, not during).
"""

import importlib.util
import json
import os
import sys
from urllib.parse import urlparse

failures = []

# Old setting name -> current one (renamed Nov 13, 2026).
RENAMED = {
    "PROVIDER_BASE_URL": "LLM_BASE_URL",
    "PROVIDER_API_KEY": "LLM_API_KEY",
    "MODEL": "LLM_MODEL",
}


def check(label, ok, hint):
    mark = "ok  " if ok else "FAIL"
    print(f"[{mark}] {label}")
    if not ok:
        failures.append(f"{label}: {hint}")


def token_limit(base_url: str, n: int) -> dict:
    """The output-token cap, under the name this provider accepts.

    OpenAI's own API rejects max_tokens for its newer models (o-series,
    gpt-5) and wants max_completion_tokens. Other OpenAI-compatible
    providers mostly still expect max_tokens.
    """
    host = urlparse(base_url).hostname or ""
    if host == "openai.com" or host.endswith(".openai.com"):
        return {"max_completion_tokens": n}
    return {"max_tokens": n}


def main() -> int:
    check(
        f"Python >= 3.11 (found {sys.version_info.major}.{sys.version_info.minor})",
        sys.version_info >= (3, 11),
        "install Python 3.11+ and recreate your virtualenv",
    )

    venv = os.environ.get("VIRTUAL_ENV")
    running_in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if venv and not running_in_venv:
        check(
            f"interpreter matches the active virtualenv (running {sys.executable})",
            False,
            "a virtualenv is active but this python is NOT from it — you likely "
            "have a shell alias (run: unalias python) or are using the wrong "
            "interpreter; then retry",
        )
    else:
        check(
            "running inside the project environment",
            running_in_venv,
            "invoke via uv: uv run setup/check_setup.py",
        )
    for module in ("openai", "pytest", "rich", "dotenv"):
        ok = importlib.util.find_spec(module) is not None
        check(f"package: {module}", ok, "run: uv sync (then invoke via uv run)")

    # Block 4 runs five production harnesses. A plain `uv sync` installs
    # them too, but check here so a missing one shows up at home rather
    # than as a download on venue WiFi.
    for module, label in (
        ("claude_agent_sdk", "Claude Agent SDK"),
        ("agents", "OpenAI Agents SDK"),
        ("google.adk", "Google ADK"),
        ("litellm", "LiteLLM (used by Google ADK)"),
        ("deepagents", "Deep Agents"),
        ("langgraph", "LangGraph"),
        ("pydantic_ai", "Pydantic AI"),
    ):
        try:
            ok = importlib.util.find_spec(module) is not None
        except ModuleNotFoundError:
            ok = False
        check(f"Block 4: {label}", ok, "run: uv sync (it installs the Block 4 frameworks too), then retry")

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    # The settings were renamed on Nov 13, 2026. A .env made before then
    # still uses the old names: say so instead of reporting them missing.
    renamed = [f"{old} -> {new}" for old, new in RENAMED.items()
               if os.environ.get(old) and not os.environ.get(new)]
    if renamed:
        check(".env uses the current setting names", False,
              "rename these in .env: " + ", ".join(renamed))

    key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")
    base_url = os.environ.get("LLM_BASE_URL", "")
    check("LLM_API_KEY is set", bool(key), "copy .env.example to .env and fill it in")
    check("LLM_MODEL is set", bool(model), "copy .env.example to .env and fill it in")
    check("LLM_BASE_URL is set", bool(base_url), "copy .env.example to .env and fill it in")

    if key and model and base_url and importlib.util.find_spec("openai"):
        from openai import OpenAI

        try:
            client = OpenAI(base_url=base_url, api_key=key)
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "Reply with the single word: ready"}],
                **token_limit(base_url, 5),
            )
            check(f"provider reachable ({base_url}, model {model})", True, "")
        except Exception as exc:
            check(
                f"provider reachable ({base_url}, model {model})",
                False,
                f"API call failed: {exc}",
            )
        else:
            # Every block depends on tool calling, and a model or proxy can
            # answer plain text perfectly well and still fail at tools. So
            # ask for one real tool call and check what comes back.
            tool_ok, tool_hint = False, ""
            try:
                reply = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content":
                               "Call the report_status tool with status set to 'ready'."}],
                    tools=[{
                        "type": "function",
                        "function": {
                            "name": "report_status",
                            "description": "Report a status word.",
                            "parameters": {
                                "type": "object",
                                "properties": {"status": {"type": "string"}},
                                "required": ["status"],
                            },
                        },
                    }],
                    **token_limit(base_url, 100),
                )
                calls = reply.choices[0].message.tool_calls or []
                if not calls:
                    tool_hint = ("the model replied in text instead of calling the tool. "
                                 "The workshop needs a model and provider that support tool calling")
                elif calls[0].function.name != "report_status":
                    tool_hint = f"the model called an unexpected tool: {calls[0].function.name}"
                else:
                    json.loads(calls[0].function.arguments or "{}")
                    tool_ok = True
            except json.JSONDecodeError:
                tool_hint = "the model's tool call arguments weren't valid JSON"
            except Exception as exc:
                tool_hint = f"tool-calling request failed: {exc}"
            check("tool calling works", tool_ok, tool_hint)

    print()
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL GREEN — see you at the workshop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
