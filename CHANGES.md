# Changes — 2026-05-16

## Context
The original project was built and tested on a specific setup. These changes make it work
across different Python versions and LLM providers without breaking the original setup.

| Component | Original setup | This setup |
|---|---|---|
| Python | 3.10 / 3.11 / 3.12 | 3.13 |
| LLM | Ollama + gemma3:9b | LM Studio + Qwen3 thinking model |
| STT | openai-whisper | faster-whisper (replacement) |

---

## Changes

### 1. `backend/requirements.txt`
**Problem:** `openai-whisper==20240930` fails to build on Python 3.13 — its `setup.py`
imports `pkg_resources` which is no longer available in modern Python/setuptools.  
**Fix:** Replaced with `faster-whisper>=1.0.3`.  
**Impact on other setups:** Improvement for everyone — faster, actively maintained, Python 3.13 compatible. No downside.

---

### 2. `backend/providers/stt/whisper_local.py`
**Problem:** Code used `openai-whisper` API (`whisper.load_model`, `model.transcribe`).  
**Fix:** Rewrote to use `faster-whisper` API (`WhisperModel`, segments-based transcribe). Also now returns `duration_seconds` which was previously unavailable.  
**Impact on other setups:** Transparent replacement. Same behaviour, better library.

---

### 3. `backend/providers/llm/openai_compatible.py`
**Problem:** Streaming loop only collected `delta.content`. Qwen3 thinking models stream
thinking tokens into `delta.reasoning_content`, leaving `delta.content` empty — all
responses came back as empty strings.  
**Fix:** Also collect `delta.reasoning_content` as a fallback via `getattr`. If `content`
is empty after streaming, wrap reasoning content in `<think>...</think>` tags for the
extractor to strip.  
**Impact on other setups:** `getattr(delta, "reasoning_content", None)` returns `None`
for Ollama/OpenAI — no effect whatsoever.

---

### 4. `backend/core/utils.py`
**Problem:** `extract_json()` only stripped markdown code fences. Thinking model output
(`<think>...</think>` blocks) and prose before/after the JSON caused `json.loads` to fail.  
**Fix:**
- Strip `<think>...</think>` blocks (handles Qwen3, DeepSeek-R1, QwQ, etc.)
- Extract outermost `{...}` to discard any prose the model adds before or after the JSON  

**Impact on other setups:** Both are no-ops for standard models — regex finds no `<think>`
tags, and `{...}` extraction still correctly finds the JSON object.

---

### 5. `backend/services/assessor.py`
**Problem:** On JSON parse failure, the retry loop fed the entire broken response (4000+
chars) back to the model as context — confusing it into returning empty content on the
next attempt.  
**Fix:**
- Retry now sends a clean fresh prompt instead of the broken response
- Added `_repair_questions_json()` that walks a truncated response character by character,
  collecting balanced `{...}` blocks, and salvages any complete question objects before
  giving up  

**Impact on other setups:** Genuine improvement for all models — any model can produce
malformed JSON on occasion. Clean retry and salvage logic helps everyone.

---

### 6. `backend/core/config.py` + `backend/core/prompt_manager.py`
**Problem:** `/no_think` was hardcoded in all prompt templates — fine for Qwen3 but
meaningless noise for Ollama/OpenAI/Anthropic.  
**Fix:** Added `no_think_mode: bool = False` to `LLMConfig`. `PromptManager` now
auto-injects this flag into every template render. Templates use
`{% if no_think_mode %}/no_think{% endif %}` so it only appears when configured.  
**Impact on other setups:** Default is `false` — prompts are sent unchanged for all
standard models. Qwen3 users set `no_think_mode: true` in `config.yaml`.

---

### 7. `prompts/*.j2` (all 6 templates)
**Problem:** `/no_think` was hardcoded — Qwen3-specific instruction visible to all models.  
**Fix:** Replaced with `{% if no_think_mode %}/no_think{% endif %}` in all 6 files:
- `prompts/summary_system.j2`
- `prompts/questions_system.j2`
- `prompts/evaluate_mcq_system.j2`
- `prompts/evaluate_voice_system.j2`
- `prompts/concept_map_system.j2`
- `prompts/confusion_map_system.j2`

**Impact on other setups:** No change for standard models. Qwen3 gets `/no_think` only
when `no_think_mode: true` is set.

---

### 8. `config.example.yaml`
**Problem:** No documentation for the `no_think_mode` option.  
**Fix:** Added `no_think_mode: false` with full comment explaining when to use it.

---

### 9. `frontend/src/pages/InputPage.tsx`
**Problem:** Error message hardcoded "Check that LM Studio server is running" regardless
of which provider was configured.  
**Fix:** Changed to: "Check that your LLM provider is running and reachable (see config.yaml)."  
**Impact on other setups:** Better for everyone.

---

### 10. `config.yaml` *(new file — not committed, user-specific)*
Created for LM Studio + Qwen3 setup:
```yaml
llm:
  provider: "lmstudio"
  model: "qwen/qwen3-4b-thinking-2507"
  temperature: 0.3
  max_tokens: 16000        # raised from 4000 — thinking tokens consume token budget fast
  timeout_seconds: 120
  no_think_mode: true   # skip <think> phase for structured JSON tasks
  lmstudio:
    base_url: "http://localhost:1234/v1"
    api_key: "lm-studio"
```

> `max_tokens: 16000` — Qwen3 thinking mode uses thousands of tokens for reasoning before
> producing output. The original default of 4000 caused the model to hit the limit inside
> the `<think>` block, leaving no tokens for the actual JSON answer.

---

## Summary — impact on each setup

| Change | Ollama + gemma3:9b | LM Studio + Qwen3 | OpenAI / Anthropic |
|---|---|---|---|
| `faster-whisper` | Better | Better | Better |
| `reasoning_content` fallback | No effect | Fixes empty responses | No effect |
| `<think>` stripping | No effect | Fixes JSON parse failures | No effect |
| `{...}` extraction | Slightly more robust | Fixes prose-wrapped JSON | Slightly more robust |
| Clean retry / salvage | More robust | More robust | More robust |
| `no_think_mode` flag | `false` → no change | `true` → adds `/no_think` | `false` → no change |
| Frontend error message | Better | Better | Better |
