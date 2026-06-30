<div align="center">

# 🧠 BinMind

**AI-assisted reverse engineering for binaries, powered by Ghidra**

Drop in an `.exe` / `.dll` / `.elf` → ask questions in plain language →
an AI agent runs the required steps in Ghidra and answers with explanations, graphs and code.

</div>

---

## What it is

BinMind is a desktop app (dark, chat-style UI) that wires together:

- **Headless Ghidra** (the open-source decompiler by the NSA, runs in Docker) — analyzes the binary;
- **An LLM agent** (local Ollama or any OpenAI-compatible API) — answers questions by
  calling Ghidra tools on its own: list functions, decompile, cross-references, imports,
  strings, artifact search;
- **A web UI** — chat with code highlighting, Markdown and **Mermaid** diagrams
  (call graphs / flowcharts).

> A reworked fork of [ReverseAI](#credits--license) by Biniam Demissie: adds a desktop
> window, in-app settings, live status indicators, RU/EN interface, an in-app setup guide,
> an offline single-file `.exe`, and a new dark theme.

## How it works

```
┌──────────────┐   HTTP    ┌─────────────────┐  function calls  ┌──────────────────┐
│  BinMind UI  │ ────────▶ │  BinMind (Flask) │ ───────────────▶ │  LLM (Ollama /   │
│ (window/chat)│ ◀──────── │  agent + proxy   │ ◀─────────────── │  OpenAI-compat.) │
└──────────────┘   SSE     └────────┬─────────┘                  └──────────────────┘
                                    │ REST (:9090)
                                    ▼
                          ┌──────────────────┐
                          │  Headless Ghidra │  (Docker)
                          └──────────────────┘
```

## Requirements

1. **Docker** — for the Ghidra container.
2. **An LLM** — one of:
   - **Ollama** locally (recommended: free, no rate limits) — https://ollama.com
   - or any cloud OpenAI-compatible API (key + URL).
3. **Python 3.10+** — only if running from source.

## Quick start

### 1. Start the backends (Ghidra + LLM)

**Easiest — one command with Docker Compose** (brings up both Ghidra and Ollama):

```bash
docker compose up -d
docker exec -it ollama ollama pull qwen2.5-coder:7b   # one-time: download a model
```

**Or manually, separately:**

```bash
# Ghidra (REST on :9090)
docker run --rm -p 9090:9090 -v binmind_data:/data/ghidra_projects biniamfd/ghidra-headless-rest:latest

# LLM — Ollama (https://ollama.com), free and unlimited
ollama serve
ollama pull qwen2.5-coder:7b
```

### 2. Launch BinMind

**Option A — prebuilt `.exe` (Windows):** download `BinMind.exe` from Releases and double-click it.

**Option B — from source:**

```bash
pip install -r requirements.txt
python main.py            # desktop window
python main.py --web      # or in the browser on localhost
```

(on Windows you can just run `run.bat`)

### 3. Configure & use

Open ⚙ **Settings** (top-right), check the LLM/Ghidra URLs, click **"Test connection"**.
The `Ghidra ●` and `LLM ●` indicators at the top should turn green.
Then: **Choose file → Analyze** → wait for `DONE` → select the job → ask.

The top-right corner also has a **RU/EN** language toggle and a **?** button —
an in-app guide for connecting Ghidra and the LLM.

Example questions:
- "What does this program do? Describe the main logic."
- "Find suspicious strings and potential C2 addresses."
- "Build a call graph of the main function as a Mermaid diagram."

## Build the `.exe`

```bash
build.bat              # Windows: installs deps + PyInstaller and builds
# or manually:
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --clean BinMind.spec
```

Output: `dist/BinMind.exe`. All templates, styles and JS libraries (marked, highlight.js,
mermaid) are **bundled inside**, so the UI works offline. The `.exe` still needs a running
Docker Ghidra and an LLM (see Requirements).

## Distribution (release with the `.exe`)

The `.exe` is not stored in git (large and reproducible) — publish it via **GitHub Releases**:

1. Build it: `build.bat` → `dist/BinMind.exe`.
2. Repo page → **Releases** → **Create a new release** → tag `v1.0.0`.
3. Drag `dist/BinMind.exe` (and optionally `docker-compose.yml`) into **Attach binaries** → **Publish**.

You can ship a single **"starter" ZIP**: `BinMind.exe` + `docker-compose.yml` + this README.
A truly self-contained single file is not possible — the Ghidra Docker image and the LLM model
(several GB) can't be embedded into an exe. But `docker compose up -d` makes starting the
backends practically one command.

## Settings & data

Settings and chat history are stored in the per-user directory (not in the repo):

- Windows: `%APPDATA%\BinMind\`
- macOS: `~/Library/Application Support/BinMind/`
- Linux: `~/.config/BinMind/`

`binmind.log` lives there too — handy when debugging the built `.exe`.
You can also configure everything via environment variables (on first run):
`API_BASE`, `API_KEY`, `MODEL_NAME`, `GHIDRA_API_BASE`.

## Project layout

```
binmind/
  server.py      # Flask: UI, Ghidra proxy, /chat (SSE), /api/settings, /api/health
  assistant.py   # LLM agent loop + Ghidra tool calls
  config.py      # settings (defaults / file / env)
  paths.py       # paths for source and PyInstaller builds
  templates/     # index.html
  static/        # css, js, vendor (offline libraries)
main.py          # entry point: window (pywebview) or browser (--web)
BinMind.spec     # single-file .exe build
docker-compose.yml  # Ghidra + Ollama backends
```

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `Ghidra ●` is red | Is the Docker container running on `:9090`? Check the URL in Settings. |
| `LLM ●` is red | Is Ollama running (`ollama serve`)? Is the model pulled? Correct Base URL/key? |
| Window is blank in the `.exe` | Check `binmind.log` in the data dir (see above). |
| Model "can't see" functions | Wait for the job status to be `DONE` before asking. |

## Credits & license

BinMind is built on top of **"AI-Assisted Reverse Engineering with Ghidra" (ReverseAI)**
by **Biniam Demissie**. Many thanks for the original idea and the REST wrapper around Ghidra.

BinMind's modifications are released under the [MIT License](LICENSE). The upstream project
is published without an explicit license — verify the licensing of the upstream code and the
Ghidra Docker image you use before redistributing publicly or commercially.
