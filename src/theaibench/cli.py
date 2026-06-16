"""Command-line interface for The AI Bench planner.

Calls the free public API at https://theaibench.ai/api/v1/plan and prints a
local-AI setup recommendation. Zero third-party dependencies — standard library
only — so it stays trivial to install (`uvx theaibench`) and maintain. Because it
reads the live API, the recommendations are always as current as the website.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

DEFAULT_API_BASE = "https://theaibench.ai"
PLAN_PATH = "/api/v1/plan"
SITE_URL = "https://theaibench.ai"
TIMEOUT_SECONDS = 20

# Param choices mirror the OpenAPI schema at theaibench.ai/api/openapi.json.
CHOICES = {
    "mode": ["current", "new"],
    "platform": ["windows", "windows-laptop", "mac", "linux"],
    "vram": ["none", "8", "12", "16", "20", "24", "32", "48", "64", "96", "128"],
    "memory": ["16", "24", "32", "36", "48", "64", "96", "128"],
    "ram": ["16", "32", "48", "64", "96", "128", "192", "256"],
    "budget": ["under1500", "1500to3000", "3000to6000", "6000plus"],
    "use_case": ["coding", "chat", "docs", "image", "agents", "voice"],
    "priority": ["privacy", "speed", "cost"],
    "gpu_family": ["nvidia", "amd", "cpu"],
    "context": ["4096", "16384", "65536", "200000"],
}

# Maps a verdict string to an ANSI color code.
VERDICT_COLORS = {
    "Strong": "92",         # bright green
    "Comfortable": "96",    # bright cyan
    "Workable": "93",       # bright yellow
    "Cloud-leaning": "95",  # bright magenta
}


class PlanError(Exception):
    """A user-facing error worth printing without a stack trace."""


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def color_enabled(force_no_color: bool) -> bool:
    """Respect NO_COLOR, --no-color, and non-tty output (pipes, CI)."""
    if force_no_color or os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


def paint(text: str, code: str, enabled: bool) -> str:
    if not enabled or not code:
        return text
    return f"\033[{code}m{text}\033[0m"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def build_params(args: argparse.Namespace) -> dict:
    """Turn parsed args into the API query dict, dropping unset values so the
    server applies its own defaults."""
    fields = {
        "mode": args.mode,
        "platform": args.platform,
        "vram": args.vram,
        "memory": args.memory,
        "ram": args.ram,
        "budget": args.budget,
        "use_case": args.use_case,
        "priority": args.priority,
        "gpu_family": args.gpu_family,
        "context": args.context,
    }
    return {k: v for k, v in fields.items() if v is not None}


def fetch_plan(params: dict, api_base: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Call the planner API and return the parsed JSON, or raise PlanError."""
    query = urllib.parse.urlencode(params)
    url = f"{api_base.rstrip('/')}{PLAN_PATH}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"theaibench-cli/{__version__} (+{SITE_URL})",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            msgs = payload.get("messages") or []
            if msgs:
                detail = ": " + "; ".join(msgs)
        except Exception:
            pass
        raise PlanError(f"API returned HTTP {exc.code}{detail}") from exc
    except urllib.error.URLError as exc:
        raise PlanError(
            f"Could not reach {api_base} ({exc.reason}). Check your connection."
        ) from exc
    except TimeoutError as exc:  # pragma: no cover - network timing
        raise PlanError(f"Request to {api_base} timed out after {timeout}s.") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise PlanError("API did not return valid JSON.") from exc


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(data: dict, use_color: bool) -> str:
    result = data.get("result") or {}
    inputs = data.get("inputs") or {}
    meta = data.get("meta") or {}

    verdict = result.get("verdict", "—")
    code = VERDICT_COLORS.get(verdict, "")
    tier = result.get("tier")
    band = result.get("band", "")

    lines: list[str] = []
    lines.append("")
    header = paint("THE AI BENCH", "1", use_color)
    tier_str = f"tier {tier} · {band} band" if tier is not None else band
    lines.append(f"  {header}  ·  {paint(verdict, code, use_color)}  ({tier_str})")
    if result.get("title"):
        lines.append(f"  {paint(result['title'], '2', use_color)}")
    lines.append("")

    if result.get("summary"):
        lines.append(f"  {result['summary']}")
        lines.append("")

    picks = result.get("picks") or []
    if picks:
        lines.append(f"  {paint('TOP PICKS', '1', use_color)}")
        for i, pick in enumerate(picks, 1):
            name = pick.get("name", "")
            why = pick.get("why", "")
            lines.append(f"  {paint(f'{i}.', code, use_color)} {paint(name, '1', use_color)}")
            if why:
                lines.append(f"     {paint(why, '2', use_color)}")
        lines.append("")

    runner = result.get("runner") or {}
    rows = []
    if runner.get("name"):
        runner_text = runner["name"]
        if runner.get("note"):
            runner_text += f" — {runner['note']}"
        rows.append(("RUNNER", runner_text))
    if result.get("quantization"):
        rows.append(("QUANT", result["quantization"]))
    if result.get("expected_speed"):
        rows.append(("SPEED", result["expected_speed"]))
    for label, value in rows:
        lines.append(f"  {paint(label.ljust(6), code, use_color)} {value}")
    if rows:
        lines.append("")

    workflow = result.get("workflow") or []
    if workflow:
        lines.append(f"  {paint('WORKFLOW', '1', use_color)}")
        for step in workflow:
            lines.append(f"    • {step}")
        lines.append("")

    watchouts = result.get("watchouts") or []
    if watchouts:
        lines.append(f"  {paint('WATCH OUT', '1', use_color)}")
        for w in watchouts:
            lines.append(f"    ! {w}")
        lines.append("")

    if result.get("note"):
        lines.append(f"  {paint(result['note'], '2', use_color)}")
        lines.append("")

    # Footer: inputs echo + attribution.
    shown = [
        inputs.get("platform"),
        (f"{inputs.get('macMemory')}GB unified" if inputs.get("platform") == "mac"
         else f"{inputs.get('pcVram')}GB VRAM"),
        inputs.get("useCase"),
        inputs.get("priority"),
    ]
    shown = [s for s in shown if s]
    if shown:
        lines.append(f"  {paint(' · '.join(str(s) for s in shown), '2', use_color)}")
    dated = meta.get("dated")
    footer = f"  Full planner → {SITE_URL}"
    if dated:
        footer += paint(f"   (data: {dated})", "2", use_color)
    lines.append(paint(footer, "2", use_color) if not dated else footer)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interactive prompts
# ---------------------------------------------------------------------------

def _prompt_choice(label: str, options: list[str], default: str) -> str:
    opts = "/".join(options)
    while True:
        raw = input(f"{label} [{opts}] ({default}): ").strip()
        if not raw:
            return default
        if raw in options:
            return raw
        print(f"  Please pick one of: {opts}")


def run_interactive(args: argparse.Namespace) -> argparse.Namespace:
    print("The AI Bench — answer a few questions (Enter = default):\n")
    args.platform = _prompt_choice("Platform", CHOICES["platform"], "windows")
    if args.platform == "mac":
        args.memory = _prompt_choice("Unified memory (GB)", CHOICES["memory"], "32")
    else:
        args.gpu_family = _prompt_choice("GPU family", CHOICES["gpu_family"], "nvidia")
        if args.gpu_family != "cpu":
            args.vram = _prompt_choice("GPU VRAM (GB)", CHOICES["vram"], "16")
        args.ram = _prompt_choice("System RAM (GB)", CHOICES["ram"], "32")
    args.use_case = _prompt_choice("Use case", CHOICES["use_case"], "coding")
    args.priority = _prompt_choice("Priority", CHOICES["priority"], "speed")
    print("")
    return args


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="theaibench",
        description=(
            "Find the best local-AI model + setup for your hardware. "
            "Powered by the free public planner API at theaibench.ai."
        ),
        epilog="Free to use and cite with attribution. Not affiliated with any vendor; no tracking.",
    )
    p.add_argument("-i", "--interactive", action="store_true",
                   help="answer questions one at a time instead of passing flags")
    p.add_argument("--platform", choices=CHOICES["platform"], help="operating platform")
    p.add_argument("--vram", choices=CHOICES["vram"], help="dedicated GPU VRAM in GB (PC only)")
    p.add_argument("--memory", choices=CHOICES["memory"], help="Mac unified memory in GB (mac only)")
    p.add_argument("--ram", choices=CHOICES["ram"], help="system RAM in GB (PC only)")
    p.add_argument("--use-case", dest="use_case", choices=CHOICES["use_case"],
                   help="what you plan to do")
    p.add_argument("--priority", choices=CHOICES["priority"], help="what matters most")
    p.add_argument("--gpu-family", dest="gpu_family", choices=CHOICES["gpu_family"],
                   help="GPU family (PC only); 'cpu' = no dedicated GPU")
    p.add_argument("--context", choices=CHOICES["context"], help="typical context window in tokens")
    p.add_argument("--mode", choices=CHOICES["mode"],
                   help="'current' (you own hardware) or 'new' (planning a build)")
    p.add_argument("--budget", choices=CHOICES["budget"], help="USD budget band (mode=new only)")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="print the raw API JSON response")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    p.add_argument("--api-base", default=os.environ.get("THEAIBENCH_API", DEFAULT_API_BASE),
                   help=argparse.SUPPRESS)
    p.add_argument("-V", "--version", action="version", version=f"theaibench {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    explicit = any(
        getattr(args, f) is not None
        for f in ("platform", "vram", "memory", "ram", "use_case",
                  "priority", "gpu_family", "context", "mode", "budget")
    )

    if args.interactive or (not explicit and sys.stdin.isatty() and sys.stdout.isatty()):
        try:
            args = run_interactive(args)
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 130

    params = build_params(args)
    try:
        data = fetch_plan(params, args.api_base)
    except PlanError as exc:
        print(f"theaibench: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(data, indent=2))
        return 0

    print(render(data, color_enabled(args.no_color)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
