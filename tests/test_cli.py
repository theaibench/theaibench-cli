"""Offline unit tests (standard-library unittest — no third-party deps).

These don't hit the network. A live smoke check lives in the `if __name__`
block, gated behind THEAIBENCH_LIVE=1.
"""

import argparse
import os
import unittest

from theaibench import cli


def _args(**kw):
    base = dict(
        mode=None, platform=None, vram=None, memory=None, ram=None, budget=None,
        use_case=None, priority=None, gpu_family=None, context=None,
    )
    base.update(kw)
    return argparse.Namespace(**base)


class BuildParams(unittest.TestCase):
    def test_drops_unset_values(self):
        params = cli.build_params(_args(platform="mac", memory="64", use_case="docs"))
        self.assertEqual(params, {"platform": "mac", "memory": "64", "use_case": "docs"})

    def test_empty_when_nothing_set(self):
        self.assertEqual(cli.build_params(_args()), {})

    def test_keeps_use_case_key_name(self):
        # The API expects snake_case `use_case` on the wire.
        params = cli.build_params(_args(use_case="coding"))
        self.assertIn("use_case", params)


class ColorHandling(unittest.TestCase):
    def test_no_color_flag_disables(self):
        self.assertFalse(cli.color_enabled(force_no_color=True))

    def test_no_color_env(self):
        prev = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        try:
            self.assertFalse(cli.color_enabled(force_no_color=False))
        finally:
            if prev is None:
                del os.environ["NO_COLOR"]
            else:
                os.environ["NO_COLOR"] = prev

    def test_paint_noop_when_disabled(self):
        self.assertEqual(cli.paint("hi", "92", enabled=False), "hi")

    def test_paint_wraps_when_enabled(self):
        self.assertEqual(cli.paint("hi", "92", enabled=True), "\033[92mhi\033[0m")


class Render(unittest.TestCase):
    SAMPLE = {
        "inputs": {"platform": "windows", "pcVram": "24", "useCase": "coding", "priority": "speed"},
        "result": {
            "verdict": "Comfortable",
            "tier": 5.25,
            "band": "high",
            "title": "Comfortable for midsize local models",
            "summary": "Strong for daily local use.",
            "picks": [{"name": "Qwen3-Coder-30B-A3B", "why": "3B-active MoE."}],
            "runner": {"name": "Ollama or LM Studio", "note": "LM Studio for UI."},
            "quantization": "Q4_K_M sweet spot.",
            "expected_speed": "30–50 tok/s on 14B.",
            "workflow": ["Wire into your editor."],
            "watchouts": ["RAM is tight."],
            "note": "Local makes sense here.",
        },
        "meta": {"dated": "April 2026"},
    }

    def test_render_plain_contains_key_fields(self):
        out = cli.render(self.SAMPLE, use_color=False)
        for needle in ["Comfortable", "Qwen3-Coder-30B-A3B", "Ollama or LM Studio",
                       "Q4_K_M", "30–50 tok/s", "theaibench.ai", "April 2026"]:
            self.assertIn(needle, out)

    def test_render_has_no_ansi_when_plain(self):
        self.assertNotIn("\033[", cli.render(self.SAMPLE, use_color=False))

    def test_render_handles_empty_result(self):
        # Should not raise on a minimal/empty payload.
        cli.render({"result": {}, "inputs": {}, "meta": {}}, use_color=False)


class Parser(unittest.TestCase):
    def test_rejects_bad_choice(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["--platform", "atari"])

    def test_accepts_valid_args(self):
        ns = cli.build_parser().parse_args(["--platform", "mac", "--memory", "64"])
        self.assertEqual(ns.platform, "mac")
        self.assertEqual(ns.memory, "64")


if __name__ == "__main__":
    if os.environ.get("THEAIBENCH_LIVE") == "1":
        data = cli.fetch_plan({"platform": "windows", "vram": "24", "use_case": "coding"},
                              cli.DEFAULT_API_BASE)
        assert data["result"]["picks"], "live API returned no picks"
        print("LIVE OK:", data["result"]["verdict"])
    unittest.main()
