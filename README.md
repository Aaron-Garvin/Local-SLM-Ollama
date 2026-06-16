# 🦙 Local SLM Benchmark — Offline AI with Ollama

> Run **3 AI models entirely on your machine** — no internet, no API keys, no cloud costs. Compare their speed and structured extraction quality side-by-side.

---

## 💡 What Does This Do?

This project spins up a local REST API that routes text extraction requests to local language models via [Ollama](https://ollama.com). A built-in benchmark then stress-tests all three models with the same prompts and tells you which one wins on your hardware.

**What you get:**
- A running `/extract` API endpoint that returns structured JSON from plain text
- A benchmark report comparing latency and extraction reliability across 3 models
- A clear, data-driven answer to: *"Which model should I use for my machine?"*

---

## 🤖 The Three Models

| Model | Pull Command | Best For |
|---|---|---|
| `mistral` | `ollama pull mistral` | Highest accuracy, worth the extra memory |
| `llama3.2` | `ollama pull llama3.2` | Best balance of speed and reliability |
| `phi3:mini` | `ollama pull phi3:mini` | Fastest; great for low-memory machines |

> All models run **100% offline** after the initial download. No data leaves your machine.

---

## ⚡ Quick Start (7 Steps)

### Step 1 — Install Ollama

**Windows:** Download and install from [ollama.com](https://ollama.com)

**macOS / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

### Step 2 — Download the Models

```bash
ollama pull mistral
ollama pull llama3.2
ollama pull phi3:mini
```

> ⏱️ This is a one-time download. Each model is ~2–4 GB, so allow a few minutes depending on your connection.

---

### Step 3 — Start Ollama

```bash
ollama serve
```

Verify it's running:

```bash
curl http://localhost:11434/api/tags
```

You should see a JSON list of your downloaded models.

---

### Step 4 — Set Up Python Environment

```bash
cd "your/project/folder"
python -m venv venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source venv/bin/activate

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

### Step 5 — Start the API Server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal open — the server needs to stay running.

---

### Step 6 — Test the API

**Health check** (confirm the server is up):
```bash
curl http://127.0.0.1:8000/health
```

**Try an extraction:**
```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "Alice Smith, born in 1990, works at Microsoft in Seattle.", "model": "mistral"}'
```

You should get back a structured JSON object with extracted fields. Try swapping `"mistral"` for `"llama3.2"` or `"phi3:mini"` to compare outputs.

---

### Step 7 — Run the Benchmark

Open a **second terminal**, activate the venv, then run:

```bash
python benchmark.py
```

This runs every prompt in `benchmark_prompts/prompts.json` against all three models, then saves a full report to `benchmark_results.json` and prints a summary table.

---

## 📊 Reading Your Benchmark Results

After running `python benchmark.py`, you'll see a table like this:

| Model | Avg Latency | Median | JSON Success | Notes |
|---|---|---|---|---|
| `mistral` | `XX.XXs` | `XX.XXs` | `XX%` | Best quality; slower |
| `llama3.2` | `XX.XXs` | `XX.XXs` | `XX%` | Best balance |
| `phi3:mini` | `XX.XXs` | `XX.XXs` | `XX%` | Fastest; lower memory |

**What each column means:**

- **Avg Latency** — mean response time per prompt; lower is faster
- **Median** — middle value after sorting; less affected by occasional slow spikes
- **JSON Success** — percentage of responses that passed schema validation; higher means more reliable structured output
- **HTTP 422 responses** — these are *intentional* signals, not bugs — they mean a model returned output that failed validation

**How to decide which model to use:**

- Need the most accurate extractions? → pick the model with the highest JSON Success
- Need the fastest responses? → pick the lowest Avg Latency
- Running on a laptop or low-RAM machine? → `phi3:mini` is your best bet

📝 **Fill in your actual results above** after running the benchmark, then add a short conclusion about which model won on your hardware.

---

## 🧪 End-to-End Test Checklist

```
[ ] curl http://localhost:11434/api/tags       → Lists your downloaded models
[ ] curl http://127.0.0.1:8000/health         → Returns {"status": "ok"} or similar
[ ] POST /extract with model=mistral          → Returns structured JSON
[ ] POST /extract with model=llama3.2         → Returns structured JSON
[ ] POST /extract with model=phi3:mini        → Returns structured JSON
[ ] python benchmark.py                       → Produces benchmark_results.json
```

---

## 📁 Project Structure

```
project/
│
├── main.py                        ← FastAPI server (/extract and /health endpoints)
├── benchmark.py                   ← Runs all models, measures latency & success rate
├── schemas.py                     ← Pydantic schema defining required extraction fields
│
├── benchmark_prompts/
│   └── prompts.json               ← Test prompts used by the benchmark
│
├── benchmark_results.json         ← Output from benchmark.py (auto-generated)
├── requirements.txt
└── README.md
```

---

## 🛠️ Troubleshooting

**`ollama: command not found`** — Ollama isn't installed or isn't in your PATH. Re-run the install command and open a fresh terminal.

**`Connection refused` on port 11434** — Ollama isn't running. Run `ollama serve` first.

**`Connection refused` on port 8000** — The FastAPI server isn't running. Start it with `uvicorn main:app --reload --host 127.0.0.1 --port 8000`.

**HTTP 422 on `/extract`** — The model returned output that didn't match the schema. This is expected occasionally, especially with `phi3:mini`. It's a quality signal, not a crash.

**Models downloading slowly** — This is normal; models are 2–4 GB each. Run the pulls before you need them.

**Out of memory / system slowdown** — Switch to `phi3:mini`, which has the smallest footprint. Avoid running multiple `ollama pull` commands simultaneously.

---

## 🧱 Tech Stack

| Component | Technology |
|---|---|
| Model Runtime | Ollama (local) |
| API Framework | FastAPI |
| Schema Validation | Pydantic + Instructor |
| Models | Mistral, LLaMA 3.2, Phi-3 Mini |
| Benchmark Output | JSON report + console summary |

---

## 💬 Why Run Models Locally?

| Concern | Local (this project) | Cloud API |
|---|---|---|
| **Privacy** | ✅ Data never leaves your machine | ❌ Sent to third-party servers |
| **Cost** | ✅ Free after hardware | ❌ Per-token billing |
| **Latency** | Depends on your hardware | Depends on network + load |
| **Setup** | Slightly more steps | Just an API key |
| **Offline use** | ✅ Works with no internet | ❌ Requires connection |

This project helps you measure whether local inference is fast enough for your specific use case — because the honest answer is: *it depends on your hardware.*
