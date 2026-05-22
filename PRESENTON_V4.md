# Presenton V4: System Design & Operator's Manual

**System Architect:** Rashid  
**Target Hardware:** Bare-metal dual AMD Radeon RX 9060 XT (32 GB VRAM total) · ROCm 7.2 · AMD Ryzen 7 3700X  
**Active Production Remote:** `rashh666/presenton` (fork of `presenton/presenton`)  
**Working Directory:** `~/my-project/presenton/` (commit here, push to `fork` remote)

---

## Part 1 — High-Level Design (HLD)

### 1.1 What Presenton V4 Is

Presenton V4 is an **offline-first, local-AI presentation generation platform**. It orchestrates a local LLM reasoning pipeline and a ComfyUI image-generation pipeline sequentially, guaranteeing zero VRAM collision crashes on consumer-grade workstation GPUs where both models cannot coexist in memory simultaneously.

### 1.2 System Architecture Topology

The system is split into four processing tiers:

```
                 ┌──────────────────────────────────────┐
                 │   Next.js Frontend (nginx → :5000)   │
                 │   (Next.js :3000, nginx :80 → :5000) │
                 └──────────────────┬───────────────────┘
                                    │  SSE / JSON REST
                                    ▼
                 ┌──────────────────────────────────────┐
                 │   FastAPI Core Engine (Docker)        │
                 │   Mem0 Presentation Memory Layer      │
                 └──────────────────┬───────────────────┘
                                    │  Internal loopback
                                    ▼
                 ┌──────────────────────────────────────┐
                 │   FastAPI GPU Proxy  (:8000)          │
                 │   presenton_proxy.py                  │
                 └─────┬──────────────────────────┬─────┘
                       │  Native subprocess        │  JSON API
                       ▼                           ▼
    ┌──────────────────────────────┐  ┌────────────────────────────┐
    │  llama-server  (:8081/8082)  │  │  ComfyUI Engine  (:8188)   │
    │  Gemma 3 27B GGUF            │  │  Z-Image-Turbo Q8_0 GGUF   │
    └──────────────┬───────────────┘  └────────────┬───────────────┘
                   │                               │
                   ▼                               ▼
         GPU 0+1 unified                   GPU 1 (sequential)
         (VRAM pool via                    (activates only after
          HIP_VISIBLE_DEVICES=0,1)          LLM VRAM is flushed)
```

**Tier responsibilities:**

| Tier | Process | Port | Role |
|------|---------|------|------|
| UI | Next.js + nginx | 5000 (host) | Browser interface, SSE streaming, real-time status |
| Engine | FastAPI (Docker) | internal | State management, document processing, export jobs |
| Proxy | `presenton_proxy.py` | 8000 | GPU gatekeeper: spawns/kills llama-server, routes LLM calls |
| Models | llama-server | 8081 (unified) | Gemma 3 text inference |
| Images | ComfyUI | 8188 | Z-Image-Turbo image synthesis |

### 1.3 Hardware & VRAM Allocation Matrix

VRAM is managed using a **Standing-Hot / Sequential Execution** split to prevent OOM collisions:

| Phase | GPU 0 (16 GB) | GPU 1 (16 GB) | Active Ports | Notes |
|-------|--------------|--------------|-------------|-------|
| Phase 1: Text Generation (Gemma 3 27B) | Gemma 3 (hot) | Gemma 3 (hot) | 8000, 8081 | Unified mode — both GPUs pool context |
| Phase 1: Text Generation (Qwen3.6 35B) | Qwen3.6 35B (row-split) | Qwen3.6 35B (row-split) | 8000, 8081 | `-sm row` splits tensors evenly; `-np 1 --kv-unified` cap VRAM |
| Idle Watchdog (~10 min) | Flushing | Flushing | 8000 | Watchdog polls every 15 s; kills after 600 s idle |
| Phase 2: Image Generation | 0 % VRAM | Z-Image-Turbo (9 GB) | 8188 | ComfyUI must only start after VRAM confirms 0 % |

> **Critical safety rule:** Never launch ComfyUI until `rocm-smi` confirms both GPUs are at 0 % VRAM. The watchdog flushes automatically after **600 seconds** (10 minutes) of inactivity.

---

## Part 2 — Low-Level Design (LLD)

### 2.1 GPU Proxy & Subprocess Manager (`presenton_proxy.py`)

`NativeModelManager` owns the full lifecycle of `llama-server` subprocesses. It is the single source of truth for GPU state.

**Unified Mode** (default, `UNIFIED_SINGLE_MODEL=true`)  
A single `llama-server` instance is spawned on port 8081 with `HIP_VISIBLE_DEVICES=0,1`, merging both RX 9060 XT cards into one 32 GB context pool. Used by both `gemma3` (27B) and `qwen36_35b` (35B, with row-split tensor parallelism).

**Dual Mode** (`UNIFIED_SINGLE_MODEL=false`)  
Separate processes: reasoner (Gemma 3) on GPU 0 / port 8081, coder (CodeGeeX4) on GPU 1 / port 8082. Not used in the current production profile.

**Model Registry** (resolved from `MODELS_HOST_PATH`):

| Key | File path | Context | Extra flags |
|-----|-----------|---------|-------------|
| `gemma3` | `models/reasoner/gemma3.gguf` | 8192 | — |
| `dagger` | `models/reasoner/dagger.gguf` | 8192 | — |
| `codegeex4` | `models/coder/codegeex4.gguf` | 16384 | — |
| `qwen36_35b` | `models/reasoner/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` | 8192 | `-np 1 --kv-unified -sm row --model-draft <mtp-heads> --spec-draft-n-max 2` |

> **Qwen3.6-35B two-file MTP setup:**
> - **Main model** — `Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` (22 GB, Q4_K_M quantisation)
> - **MTP draft model** — `mtp-Qwen_Qwen3.6-35B-A3B-Q4_0.gguf` (1.2 GB, MTP prediction heads only)
> - **Total VRAM** — ~23.2 GB, well within the 32 GB ceiling
>
> `-np 1` forces single-slot mode; `--kv-unified` pools KV cache across both GPUs; `-sm row` splits tensors by rows across GPU 0 & 1; `--model-draft` loads the dedicated 1.2 GB MTP heads file (not a second full model copy); `--spec-draft-n-max 2` drafts 2 tokens ahead per cycle (~37 t/s baseline → ~60+ t/s). `--mmap` is intentionally absent — direct VRAM load is faster and more reliable than the memory-mapped path on ROCm for models of this size. All flags are injected automatically.
>
> **Load time:** Expect 2–3 minutes for the combined 23.2 GB to load. The proxy startup timeout is set to **300 seconds** to accommodate this. Watch for `Unified model process healthy.` in the Terminal 1 log before sending any requests.
>
> **Note on flag format:** The updated llama.cpp arg parser (post-8375-line overhaul) enforces strict GNU formatting — `--model-draft` and `--spec-draft-n-max` require double-dash (`--`). The legacy `--draft` flag has been removed from the new binary.

**Idle Watchdog**  
Runs as a background asyncio task, polling every **15 seconds**. If `time.time() - last_activity[role]` exceeds `settings.idle_timeout` (**600 s**), it hard-terminates the subprocess, flushing VRAM completely. Streaming responses reset the timer on every chunk via a heartbeat call.

**Pass-through proxy**  
All `/v1/chat/completions` requests from the Docker container arrive at port 8000. The proxy forwards them to llama-server at port 8081, spawning the model on demand if it is not already hot.

### 2.2 Persona System & The Hallucination Power Button

The persona is selected in the UI and injected as an `x-persona` HTTP header (or `?persona=` query param for SSE streams). It flows through the entire generation pipeline.

Persona definitions live in `personas.json` at the repository root. The schema is intentionally declarative — changing behaviour requires editing JSON, not Python.

#### 2.2.1 Core Inference Parameters

| Field | `rashid_strict` | `rashid_creative` | Effect |
|-------|----------------|------------------|--------|
| `temperature` | `0.0` | `0.8` | Strict = greedy decoding; Creative = broad vocabulary |
| `top_p` | `0.1` | `0.95` | Strict = high-confidence tokens only |
| `reflection_enabled` | `true` | `false` | Enables multi-pass schema validation loop |
| `reflection_max_iterations` | `2` | `1` | Max correction cycles before accepting output |

**Reflection loop** (`generate_slide_content.py` → `generate_structured_with_schema_retries`):  
When `reflection_enabled = true`, the LLM output is validated against the slide's JSON schema. If fields are missing or malformed, a correction prompt is sent back and the loop retries up to `reflection_max_iterations` times before accepting the best result.

#### 2.2.2 Persona Context Extensions (V4)

Each persona carries additional optional blocks that are injected as natural-language constraints directly into the LLM system prompt:

| Block | Where injected | Effect |
|-------|---------------|--------|
| `audience` | Outline system prompt | Injects expertise level, domain, and primary reader type |
| `narrative_engine` | Outline system prompt | Enforces a story arc (e.g., Problem → Impact → ROI → CTA) |
| `slide_types` | Slide content system prompt | Per-beat layout rules (title slide, stats slide, etc.) |
| `business_logic` | Outline system prompt | Domain assumptions; phrases to avoid |
| `confidence_rules` | Outline system prompt | Uncertainty phrasing; avoids absolute claims |
| `visual_rules` | Image prompt assembly | Negative prompt appended to ComfyUI workflow |
| `presentation_pacing` | Slide content system prompt | Slides-per-chapter and chapter transition hints |
| `speaker_notes` | Slide content system prompt | Style, length, and transition-cue rules for speaker notes |
| `executive_mode` | Outline system prompt | Hard constraint: `CONSTRAINT: Do not exceed N slides` |

#### 2.2.3 PPTX Post-Processing (`pptx_postprocess.py`)

After Node.js exports the PPTX archive, Python-pptx opens it on the CPU and applies persona-driven decorations configured in `post_processing`:

| Decoration | `rashid_strict` | `rashid_creative` |
|-----------|----------------|------------------|
| Bottom colour bar | ✅ `bottom_bar_color_index: 1` → `#2D9CDB` | ❌ disabled |
| Signature watermark | `/app_data/rashid_logo.png` | `/app_data/rashid_creative_logo.png` |
| Fixed slide margins | `0.5 in` (top/right/bottom/left) | not set |

Place your logo PNGs at the paths above inside the Docker volume (`./app_data/` on the host).

### 2.3 Server-Side Web Grounding (`utils/web_search.py`)

Local models cannot call browser APIs, so Presenton runs a **pre-retrieval loop** on the FastAPI server before any LLM generation begins:

```
User prompt: "Q3 Fintech Trends"
        │
        ▼
LLM Query Generator (Gemma 3 @ temp=0.0)
        │
        ▼ 2–3 search query strings
        │
        ├─ TAVILY_API_KEY set? ──► Yes ──► Tavily structured JSON
        └─ No ──────────────────► DuckDuckGo (thread-safe, non-blocking)
        │
        ▼ Title + Snippet + URL per result
        │
        ▼
"# Web Search Grounding\n..." Markdown block
        │
        ├──► Prepended to Outline system prompt
        └──► Prepended to Slide Content system prompt
              (Gemma 3 is instructed to prefer these facts over training data)
```

All failures are **non-fatal** — a warning is logged and generation proceeds without grounding. Enable via the **Web Search** toggle in Advanced Settings.

### 2.4 Mem0 Presentation Memory Layer

The `MEM0_PRESENTATION_MEMORY_SERVICE` stores generation context per presentation ID:

- **At outline time:** system prompt, user prompt, extracted document text, source content, and instructions are stored.
- **After outline generation:** the final outline JSON is stored.

This gives the slide-content generation stage full recall of what was decided during outline generation, improving consistency across slides without re-sending the full context in every request.

---

## Part 3 — Environment Variables Reference

All variables are set in `~/my-project/.env` (read by the proxy) and passed through `docker-compose.yml` to the Docker container.

### Proxy (host, read by `presenton_proxy.py`)

| Variable | Default | Description |
|----------|---------|-------------|
| `MODELS_HOST_PATH` | `/home/rashid/my-project/models` | Root directory for all GGUF model files |
| `LLAMA_SERVER_BIN` | `/home/rashid/llama.cpp/build/bin/llama-server` | Path to compiled llama-server binary |
| `UNIFIED_SINGLE_MODEL` | `true` | `true` = single process, both GPUs pooled |
| `REASONER_MODEL_KEY` | `gemma3` | Key in the model registry to load (`gemma3` or `qwen36_35b`) |
| `IDLE_TIMEOUT` | `600` | Seconds before watchdog flushes VRAM |
| `LLM_TIMEOUT` | `600` | HTTP timeout for forwarded LLM requests |
| `process_startup_timeout` | `300` | Seconds the proxy waits for llama-server `/health` to return 200 before killing and retrying — raised from 120 s to accommodate the 22 GB + 1.2 GB two-model load |

### Docker Container (set in `docker-compose.yml` `production-amd` service)

| Variable | Value | Description |
|----------|-------|-------------|
| `LLM` | `custom` | LLM provider; `custom` = OpenAI-compatible URL |
| `CUSTOM_LLM_URL` | `http://host.docker.internal:8000/v1` | Routes to the host proxy |
| `CUSTOM_MODEL` | `gemma3` | Model name sent in API requests |
| `IMAGE_PROVIDER` | `disabled` / `comfyui` / `pexels` | Image source |
| `COMFYUI_URL` | `http://host.docker.internal:8188` | ComfyUI endpoint |
| `TAVILY_API_KEY` | *(optional)* | If set, used instead of DuckDuckGo for web search |
| `MEM0_ENABLED` | `false` | Enable Mem0 persistent memory |
| `APP_DATA_DIRECTORY` | `/app_data` | Mounted from `./app_data` on host |

---

## Part 4 — Operator's Manual & Runbook

### 4.1 Pre-Boot: Hardware Safety Profiles

GPU 1 (image generation) tends to spike to ~92 °C during inference. Set safety limits before launching anything:

```bash
# Force fans to 100% on GPU 1
sudo $(which rocm-smi) -d 1 --setfan 255

# Cap power draw to 175 W
/opt/rocm/bin/rocm-smi -d 1 --setpoweroverdrive 175
```

Restore after session:
```bash
/opt/rocm/bin/rocm-smi -d 1 --resetpoweroverdrive
sudo $(which rocm-smi) -d 1 --resetfans
```

### 4.2 The 3-Terminal Execution Sequence

#### Terminal 1 — GPU Proxy (Hardware Manager)

```bash
cd ~/my-project
source venv/bin/activate
uvicorn presenton_proxy:app --host 0.0.0.0 --port 8000
```

**Verify:** Log shows `✅ Native reasoner active on GPU 0,1.`

#### Terminal 2 — Presenton UI (Docker)

```bash
cd ~/my-project/presenton
docker compose --profile amd up production-amd
```

**Verify:** Navigate to `http://localhost:5000/upload`. The **My Signature** dropdown and **Colour** picker should be visible at the bottom of the screen.

> To rebuild after code changes:
> ```bash
> docker compose --profile amd build production-amd
> docker compose --profile amd up production-amd
> ```

#### Terminal 3 — ComfyUI (Image Engine)

> ⚠️ **CRITICAL:** Only open this terminal after `rocm-smi` confirms 0 % VRAM on both GPUs. The watchdog clears VRAM 600 seconds after the last LLM request. Do not skip this wait.

```bash
cd ~/my-project/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188
```

### 4.3 UI Operations Guide

```
+──────────────────────────────────────────────────────────────────+
│ [P]                                                     < Back  │
│                          Generate                               │
│            Turn prompts or documents into slides                │
│                                                                 │
│  +─────────────────────────────────────────────────────────+   │
│  │ Write prompt                                            │   │
│  │  "Company Q3 performance review"                        │   │
│  +─────────────────────────────────────────────────────────+   │
│  [⬆ Upload]  [🔍 Web Search (Advanced)]                        │
│                                                                 │
│  🎨 Colour: [#1E3A5F]    ✨ My Signature: [ Strict ▾ ]        │
│                                                 [Get Started >] │
+──────────────────────────────────────────────────────────────────+
```

**My Signature (Persona / Hallucination Power Button)**

- `rashid_strict` — temp 0.0, top_p 0.1, reflection on (2 passes). Use for financial reports, security procedures, factual briefs.
- `rashid_creative` — temp 0.8, top_p 0.95, reflection off. Use for marketing decks, brainstorming, narrative storytelling.

**Colour Override**  
Click the colour circle to pick a hex value. This is sent as `x-palette-override` and overrides the primary accent in that session. Does not permanently alter the persona's `visual_palette`.

**Web Search (Advanced Settings)**  
Toggle on to trigger the pre-retrieval loop. The engine queries 2–3 auto-generated search terms, collects live facts, and injects them into Gemma 3's context before generating any text.

**During Generation**  
The active slide being written shows a **pulsing violet ring and dot**. A progress bar displays `Writing slide N of M`. After streaming completes, if images are still being fetched, a `Fetching images…` badge appears on affected slides.

**Per-Slide Actions** (hover over any slide in the presentation view)

| Button | Action |
|--------|--------|
| ↺ Regenerate | Re-runs Gemma 3 for this slide only, using the active persona |
| ✓ Proofread | Proofreads at temp=0.0, correcting spelling and grammar without altering layout or images |

**Copy All** (header button): Exports the full deck as formatted Markdown to clipboard.

### 4.4 Development Workflow

All code changes are made in `~/my-project/presenton/`. The running Docker image must be rebuilt for changes to take effect.

```bash
# 1. Make and test changes in ~/my-project/presenton/

# 2. Commit
git -C ~/my-project/presenton add <files>
git -C ~/my-project/presenton commit -m "feat: ..."

# 3. Rebuild image
cd ~/my-project/presenton
docker compose --profile amd build production-amd

# 4. Restart container
docker compose --profile amd up production-amd -d

# 5. Push to fork
git -C ~/my-project/presenton push fork main
```

> `~/presenton/` is a separate installation used for reference only. All development happens in `~/my-project/presenton/`.

---

## Part 5 — Diagnostics & Troubleshooting

### Q1: "My Signature" dropdown is not visible

**Cause:** The FastAPI proxy in Terminal 1 is down or a zombie `llama-server` process is blocking port 8000.

**Fix:**
```bash
pkill -f llama-server          # clear any hung processes
# restart Terminal 1
uvicorn presenton_proxy:app --host 0.0.0.0 --port 8000
```

### Q2: Code or style changes not appearing in the browser

**Cause:** Next.js production bundles are cached in the browser or the Docker image was not rebuilt.

**Fix:**
1. Hard-refresh: `Ctrl+F5` (Linux/Windows) or `Cmd+Shift+R` (Mac).
2. If still stale, rebuild the image:
```bash
cd ~/my-project/presenton
docker compose --profile amd build --no-cache production-amd
docker compose --profile amd up -d --force-recreate production-amd
```

### Q3: OOM (Out of Memory) crash during image generation

**Cause:** ComfyUI was launched before the watchdog completed its 600-second flush cycle, causing Gemma 3 (~14 GB) and Z-Image-Turbo (~9 GB) to collide in VRAM.

**Fix:**
```bash
# 1. Stop ComfyUI (Ctrl+C in Terminal 3)
# 2. Force-kill any residual llama-server
pkill -f llama-server
# 3. Verify VRAM is clear
rocm-smi
# 4. Wait for 0% VRAM, then relaunch ComfyUI
```

### Q4: Web Search returns no results

**Cause:** Both Tavily and DuckDuckGo failed (network issue, rate limit, or blocked). This is non-fatal — generation continues without grounding.

**Fix:** Check FastAPI logs for `[web_search]` warning lines. Set `TAVILY_API_KEY` in the container environment for a more reliable search backend.

### Q5: Watermark or colour bar missing from exported PPTX

**Cause:** The logo PNG is not present at the path configured in `personas.json`.

**Fix:** Copy your logo to `~/my-project/presenton/app_data/rashid_logo.png` (strict) or `rashid_creative_logo.png` (creative). The Docker volume mounts `./app_data` to `/app_data` inside the container.

### Q6: Container fails to start with "network not found" error

**Cause:** Docker has a stale network entry from a previous container.

**Fix:**
```bash
docker network prune -f
cd ~/my-project/presenton
docker compose --profile amd up production-amd -d
```

---

*Document version: V4.1 — last updated 2026-05-20*
