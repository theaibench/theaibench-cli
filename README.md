# The AI Bench — CLI

**Find the best local-AI model and setup for your hardware, from your terminal.**

Tell it your platform, GPU/VRAM (or Mac unified memory), and what you want to do, and it returns a dated, opinionated recommendation: which models to run, the runner to use, quantization advice, and an expected tokens/sec band — the same logic that powers [theaibench.ai](https://theaibench.ai).

```
$ uvx theaibench --platform windows --vram 24 --use-case coding

  THE AI BENCH  ·  Comfortable  (tier 5.25 · high band)
  Comfortable for midsize local models

  Strong for daily local use, coding, and experimentation.

  TOP PICKS
  1. Qwen3-Coder-30B-A3B (MoE, fits 24GB)
     3B-active MoE — benchmark champion for local coding at this tier.
  2. Qwen 3.5 35B-A3B (generalist MoE)
     Often wins real mixed-codebase work over the Coder variant; Apache 2.0.
  3. gpt-oss-20b
     OpenAI Apache 2.0; 21B MoE with 3.6B active; near o4-mini reasoning; fits 16GB.

  RUNNER Ollama or LM Studio — LM Studio for UI, Ollama for CLI + API.
  QUANT  Q4_K_M is the sweet spot at 14B. MoE 30B-A3B runs at 3B-dense speed.
  SPEED  50–70 tok/s on 8B, 30–50 on 14B Q4, 20–35 on 30B-A3B MoE.

  Full planner → https://theaibench.ai
```

## Install / run

No install needed with [uv](https://docs.astral.sh/uv/):

```bash
uvx theaibench                       # interactive — answer a few questions
uvx theaibench --platform mac --memory 64 --use-case docs
```

Or install it:

```bash
pipx install theaibench       # isolated
pip install theaibench        # into the current environment
```

## Usage

```
theaibench [options]

  --platform     windows | windows-laptop | mac | linux
  --vram         GPU VRAM in GB (PC):  none 8 12 16 20 24 32 48 64 96 128
  --memory       Mac unified memory in GB:  16 24 32 36 48 64 96 128
  --ram          system RAM in GB (PC):  16 32 48 64 96 128 192 256
  --gpu-family   nvidia | amd | cpu        (cpu = no dedicated GPU)
  --use-case     coding | chat | docs | image | agents | voice
  --priority     privacy | speed | cost
  --context      4096 | 16384 | 65536 | 200000   (typical prompt length)
  --mode         current | new            (new = planning a build, uses --budget)
  --budget       under1500 | 1500to3000 | 3000to6000 | 6000plus
  -i, --interactive   answer questions one at a time
  --json              print the raw API response
  --no-color          disable colored output
```

Run with no flags in a terminal and it walks you through the questions. Any flags you omit fall back to sensible defaults (Windows · 16 GB VRAM · coding · speed · NVIDIA).

### Examples

```bash
# Mac Studio for long-document work
theaibench --platform mac --memory 96 --use-case docs --context 65536

# Budget NVIDIA box for image generation
theaibench --platform windows --vram 16 --use-case image

# CPU-only, privacy-first
theaibench --platform linux --gpu-family cpu --ram 64 --priority privacy

# Pipe the raw data somewhere
theaibench --platform mac --memory 64 --json | jq '.result.picks'
```

## How it works

This is a thin, **zero-dependency** (standard-library-only) client over the free public planner API:

```
GET https://theaibench.ai/api/v1/plan
```

Because it reads the live API, recommendations stay as current as the website — model and hardware data are refreshed there on an ongoing basis. The full API is documented at [theaibench.ai/api/](https://theaibench.ai/api/) (OpenAPI schema included), and the agent/automation integration guide is at [theaibench.ai/for-agents/](https://theaibench.ai/for-agents/).

## Notes

- **Free** to use and cite, with attribution.
- **No tracking, no accounts, no ads.** The CLI sends only the hardware/use-case parameters you provide.
- **Not affiliated** with NVIDIA, Apple, Ollama, LM Studio, or any model vendor.
- Requires Python 3.9+.

## License

[MIT](LICENSE).
