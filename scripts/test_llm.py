"""Quick connection test for the LLM provider configured in .env.

    uv run scripts/test_llm.py
    uv run scripts/test_llm.py --prompt "Say hi" --max-tokens 50
    uv run scripts/test_llm.py --input-price 0.60 --output-price 2.20

Sends one chat completion to PROVIDER_BASE_URL with MODEL and prints the
provider, model, latency, token usage, and cost. Cost comes from the
provider's response when it reports one (e.g. usage.cost); otherwise it is
estimated from --input-price/--output-price (USD per million tokens), or
the INPUT_PRICE_PER_M / OUTPUT_PRICE_PER_M env vars, when supplied.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import OpenAI

KNOWN_PROVIDERS = {
    "baseten.co": "Baseten",
    "fireworks.ai": "Fireworks",
    "openai.com": "OpenAI",
    "openrouter.ai": "OpenRouter",
    "together.xyz": "Together",
    "groq.com": "Groq",
    "deepseek.com": "DeepSeek",
    "anthropic.com": "Anthropic",
}


def provider_name(base_url: str) -> str:
    host = urlparse(base_url).hostname or base_url
    for suffix, name in KNOWN_PROVIDERS.items():
        if host == suffix or host.endswith("." + suffix):
            return name
    if host in ("localhost", "127.0.0.1", "::1"):
        return f"local proxy ({urlparse(base_url).netloc})"
    return host


def env_price(name: str) -> float | None:
    value = os.getenv(name)
    return float(value) if value else None


def as_dict(obj) -> dict:
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_none=True)
    return dict(obj)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prompt", default="Reply with exactly: connection ok")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--input-price", type=float, help="USD per million input tokens")
    parser.add_argument("--output-price", type=float, help="USD per million output tokens")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    base_url = os.getenv("PROVIDER_BASE_URL")
    api_key = os.getenv("PROVIDER_API_KEY")
    model = os.getenv("MODEL")
    missing = [k for k, v in (("PROVIDER_BASE_URL", base_url),
                              ("PROVIDER_API_KEY", api_key),
                              ("MODEL", model)) if not v]
    if missing:
        print(f"Missing in .env: {', '.join(missing)}", file=sys.stderr)
        return 2

    input_price = args.input_price if args.input_price is not None else env_price("INPUT_PRICE_PER_M")
    output_price = args.output_price if args.output_price is not None else env_price("OUTPUT_PRICE_PER_M")

    print(f"Provider : {provider_name(base_url)}")
    print(f"Base URL : {base_url}")
    print(f"Model    : {model}")
    print(f"Prompt   : {args.prompt!r}")
    print()

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=60)
    start = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": args.prompt}],
            max_tokens=args.max_tokens,
        )
    except Exception as exc:  # report any connection/auth/model error plainly
        elapsed = time.perf_counter() - start
        print(f"FAILED after {elapsed:.2f}s: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    elapsed = time.perf_counter() - start

    choice = resp.choices[0] if resp.choices else None
    content = (choice.message.content or "").strip() if choice else ""
    usage = as_dict(resp.usage)

    print(f"Response : {content!r}")
    print()
    print("Metadata")
    print(f"  id             : {resp.id}")
    print(f"  model (served) : {resp.model}")
    print(f"  finish_reason  : {choice.finish_reason if choice else None}")
    print(f"  latency        : {elapsed:.2f}s")
    if getattr(resp, "system_fingerprint", None):
        print(f"  fingerprint    : {resp.system_fingerprint}")

    print()
    print("Usage")
    if not usage:
        print("  (provider returned no usage block)")
    in_tok = usage.get("prompt_tokens")
    out_tok = usage.get("completion_tokens")
    print(f"  input tokens   : {in_tok}")
    print(f"  output tokens  : {out_tok}")
    print(f"  total tokens   : {usage.get('total_tokens')}")
    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens")
    reasoning = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if cached is not None:
        print(f"  cached input   : {cached}")
    if reasoning is not None:
        print(f"  reasoning      : {reasoning}")
    if out_tok and elapsed > 0:
        print(f"  throughput     : {out_tok / elapsed:.1f} output tok/s (incl. network)")
    # Any provider-specific usage fields not shown above.
    shown = {"prompt_tokens", "completion_tokens", "total_tokens",
             "prompt_tokens_details", "completion_tokens_details", "cost"}
    for key, value in usage.items():
        if key not in shown:
            print(f"  {key:<15}: {value}")

    print()
    print("Cost")
    if "cost" in usage:
        print(f"  reported by provider : ${float(usage['cost']):.6f}")
    elif input_price is not None and output_price is not None and in_tok is not None and out_tok is not None:
        cost = (in_tok * input_price + out_tok * output_price) / 1_000_000
        print(f"  estimated            : ${cost:.6f} "
              f"(at ${input_price}/M in, ${output_price}/M out)")
    else:
        print("  unavailable: provider reported none; pass --input-price and "
              "--output-price (USD per million tokens) to estimate")

    print()
    print("CONNECTION OK" if choice else "CONNECTED, but no choices returned")
    return 0 if choice else 1


if __name__ == "__main__":
    sys.exit(main())
