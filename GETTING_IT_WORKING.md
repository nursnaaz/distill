# How We Got Distill Working — Session Notes

**Date:** 17 May 2026  
**Machine:** Windows 11, 16 GB RAM, CPU-only (no GPU)  
**Final result:** Full transcript analysis in ~37 seconds using Anthropic Claude Haiku

---

## Where We Started

The project existed but wasn't running cleanly. GitHub Copilot had added a `config.yaml` file that the codebase wasn't originally using — we verified the backend was actually reading it before making any changes.

The original config pointed to LM Studio as the LLM provider, so we went down that path first.

---

## Attempt 1 — Phi-2 on LM Studio

**What we tried:** Loaded Phi-2 (1.86 GB) in LM Studio and ran the backend against it.

**Problems hit:**

| Problem | What caused it | How we fixed it |
|---------|---------------|-----------------|
| Analysis always stopped at chunk 3 | `asyncio.Semaphore(3)` fired 3 concurrent requests; LM Studio rejected the 3rd | Changed `Semaphore(3)` → `Semaphore(1)` in `analyzer.py` so chunks are processed one at a time |
| LM Studio server not running | Forgot to start it | `lms server start` from CLI |
| Phi-2 kept generating forever, hit token cap | Phi-2 is a base model with no instruction tuning — it doesn't know when to stop | Reduced `max_tokens` to 600 as a hard safety cap |
| `n_keep >= n_ctx: 2152 >= 2048` error | Phi-2 has only a 2048-token context window; merged summaries exceeded it | Needed a model with larger context |

**Lesson:** Phi-2 is not suitable — it's a base model that loops, and its 2048-token context is too small for Distill's merge pass.

---

## Attempt 2 — Phi-3.1-mini on LM Studio

**What we tried:** Downloaded `Phi-3.1-mini-4k-instruct` (IQ3_M quantization, ~1.7 GB) and switched to it.

**Problems hit:**

| Problem | What caused it | How we fixed it |
|---------|---------------|-----------------|
| Still saw two models loaded | Accidentally loaded the model twice in LM Studio | Opened the Developer tab → ejected the duplicate `:2` instance |
| Config change had no effect | `uvicorn --reload` only watches `.py` files, not YAML | Always manually restart uvicorn after editing `config.yaml` |
| Model still looped, hit max_tokens | IQ3_M is 3-bit quantization — too aggressive, model loses ability to emit stop tokens | No fix; this is a fundamental limitation of over-quantized models |
| Merge pass triggered recursion | Looping model produced 1,500+ tokens (~6,000 chars) which exceeded `chunk_size_chars`, causing `_distill()` to re-chunk recursively | No fix at this stage; need a better model |
| Summary pass returned prose, not JSON | Model couldn't follow the JSON schema instruction | Added `extract_json()` improvements to find embedded JSON in prose, plus a `_make_fallback_summary()` function so the run doesn't fail completely |

**Lesson:** IQ3_M (3-bit) quantization is too aggressive for instruction-following tasks. Minimum viable quantization is Q4_K_M. Also: even with a better model, CPU-only inference on this machine was ~0.91 tokens/second — extremely slow for a 5-chunk transcript.

---

## Features We Added Along the Way

While waiting for slow local runs, we built three improvements that are now part of the app:

### 1. Resilient JSON parsing
Local models sometimes return explanation prose wrapped around the JSON, or slightly malformed JSON. We improved `extract_json()` in `backend/core/utils.py` to scan for embedded `{...}` blocks, and added `_make_fallback_summary()` in `analyzer.py` so the pipeline produces *something* usable even when JSON parsing fails completely.

### 2. Live system stats (CPU % + RAM)
Added `psutil` to the backend (`backend/routers/analyze_stream.py`). While the analysis runs, the server emits a `stats` SSE event every second (during the keepalive tick) with:
- CPU usage %
- RAM used / total (GB)
- Elapsed seconds

This appears as a live banner in the frontend while the analysis is running.

### 3. Model recommendation banner
If CPU stays above 85% for more than 2 minutes, the stats event includes a `recommendation` field. The frontend (`InputPage.tsx`) displays this as a yellow warning suggesting faster alternatives (Claude Haiku or Gemini Flash). This helps anyone on a slow CPU machine understand what's happening and what they can do.

---

## The Switch to Anthropic API

After the slow local model experience, we switched to Anthropic's API. Steps taken:

1. **Got API credits** — signed up at [console.anthropic.com](https://console.anthropic.com), bought $5 in credits (~200 runs at ~$0.02 each). Note: API credits are separate from Claude.ai subscriptions. They are one-time credits, not a monthly plan, and expire after 1 year.

2. **Set the API key** — added `ANTHROPIC_API_KEY=sk-ant-...` to `.env`

3. **Updated `config.yaml`:**
   ```yaml
   llm:
     provider: "anthropic"
     model: "claude-haiku-4-5-20251001"
     temperature: 0.3
     max_tokens: 3000
     chunk_size_chars: 8000
     chunk_overlap_chars: 500
   ```

4. **Hit a 404 on first run** — the model ID in the config was `claude-haiku-3-5` (wrong). Correct ID is `claude-haiku-4-5-20251001`.

5. **Questions generation failed** — `max_tokens: 1500` was too small for 8 questions in JSON format. Increased to `3000`.

6. **Restarted uvicorn** after each config change (mandatory — `--reload` doesn't watch YAML).

---

## Final Working State

After fixing the model name and token limit, the app ran perfectly:

```
✓ 📄 Reading transcript
✓ ✂️  Splitting into chunks
✓ 🔍 Summarizing chunk 1/5 ... 5/5
✓ 🔗 Merging summaries
✓ 📝 Topics & Concepts
✓ 🗺️  Concept Map
✓ 🎯 Quiz Questions
✓ 💾 Saving

Total time: ~37 seconds
```

**Output for a GPT/RLHF lecture transcript:**
- Session title: *"GPT Evolution and Architecture: From Mini-GPT to InstructGPT with RLHF"*
- 8 topics, 14 key concepts
- Full Mermaid concept map
- 9 quiz questions (MCQ + Teach-It-Back)

---

## Key Takeaways

| What we learned | Why it matters |
|-----------------|----------------|
| Base models (Phi-2) loop without stop tokens | Always use an instruction-tuned model |
| IQ3_M quantization breaks instruction following | Use Q4_K_M minimum for local models |
| `uvicorn --reload` ignores YAML changes | Always restart backend after `config.yaml` edits |
| `asyncio.Semaphore(1)` for local LLM servers | LM Studio doesn't queue concurrent requests |
| API credits ≠ Pro subscription | They are separate products with separate billing |
| `max_tokens` is a safety cap, not a quality ceiling | A good model stops naturally before the cap |
| Cloud API on CPU-only machine: 37s vs 10+ minutes locally | For class use, a cloud provider is the practical choice |

---

## Final `config.yaml` (working values)

```yaml
llm:
  provider: "anthropic"
  model: "claude-haiku-4-5-20251001"
  temperature: 0.3
  max_tokens: 3000
  timeout_seconds: 120
  chunk_size_chars: 8000
  chunk_overlap_chars: 500

speech_to_text:
  provider: "whisper_local"
  whisper_local:
    model_size: "base"
    device: "cpu"
    download_on_startup: false
```
