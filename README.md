# Project 2: Local SLM App with Ollama

This repository implements a fully offline local SLM benchmark using Ollama, FastAPI, and Instructor. It runs three local models on your machine, evaluates structured JSON extraction quality, and compares inference latency and success across models.

## Project goals

- Run models entirely offline using Ollama
- Compare inference speed and reliability for 3 models on the same hardware
- Evaluate structured JSON extraction quality vs latency
- Show practical tradeoffs for privacy, cost, and latency

## What is included

- `main.py` — FastAPI server exposing `/extract` and `/health`
- `benchmark.py` — benchmark runner for latency and JSON success
- `schemas.py` — Pydantic schema for required extraction fields
- `benchmark_prompts/prompts.json` — evaluation prompts for all models
- `requirements.txt` — Python dependencies
- `README.md` — project instructions and benchmark guidance

## Models in this benchmark

| Model       | Pull command            | Notes                                              |
| ----------- | ----------------------- | -------------------------------------------------- |
| `mistral`   | `ollama pull mistral`   | Highest quality/reliability, larger resource usage |
| `llama3.2`  | `ollama pull llama3.2`  | Balanced speed and success rate                    |
| `phi3:mini` | `ollama pull phi3:mini` | Lightweight, best for lower-memory systems         |

## Why this project is useful

- **Privacy:** all inference stays on your machine
- **Latency:** you can measure how fast each model is locally
- **Cost:** avoids cloud inference fees, trading cost for local compute
- **Comparison:** same prompt set on the same hardware gives fair model comparison

## What to expect

- `mistral` should be the most accurate but may be slower
- `llama3.2` should offer the best balance of speed and reliability
- `phi3:mini` is likely the fastest with the smallest memory footprint, but may produce more parse failures
- HTTP 422 responses indicate extraction validation failures, which are meaningful quality signals in this benchmark

## How to run

### 1. Install Ollama

- **Windows:** download and install from https://ollama.com
- **Linux/macOS:**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

### 2. Download the models

```bash
ollama pull mistral
ollama pull llama3.2
ollama pull phi3:mini
```

### 3. Run Ollama

```bash
ollama serve
```

Verify the server is available:

```bash
curl http://localhost:11434/api/tags
```

### 4. Set up Python environment

```bash
cd "c:/Users/Admin/Desktop/Projec-2 Local SLM via Ollama"
python -m venv venv
```

Activate the venv:

- PowerShell:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- CMD:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- Linux/macOS:
  ```bash
  source venv/bin/activate
  ```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 5. Start the API server

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Test the API

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Example extraction:

```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"text":"Alice Smith, born in 1990, works at Microsoft in Seattle.","model":"mistral"}'
```

### 7. Run the benchmark

In a second terminal with the venv active:

```bash
python benchmark.py
```

The benchmark writes results to `benchmark_results.json` and prints the performance summary.

## Benchmark interpretation

- **Avg Latency** shows model speed on this hardware
- **Median** removes outlier latency spikes
- **JSON Success** measures how often structured extraction passed validation
- **Higher success + lower latency** is better for production use

## Suggested documentation updates after benchmark

Replace the placeholder table below with your actual results after running `python benchmark.py`:

| Model       | Avg Latency | Median   | JSON Success | Notes                 |
| ----------- | ----------- | -------- | ------------ | --------------------- |
| `mistral`   | `XX.XXs`    | `XX.XXs` | `XX%`        | best quality; slower  |
| `llama3.2`  | `XX.XXs`    | `XX.XXs` | `XX%`        | best balance          |
| `phi3:mini` | `XX.XXs`    | `XX.XXs` | `XX%`        | fastest, lower memory |

Then add your conclusion:

- which model is best for quality
- which model is best for latency
- which model is best for lower-memory offline deployment
- whether offline local inference is worth the privacy/cost tradeoff for your hardware

## Notes

- This project is already structured as a local SLM benchmark.
- You should keep the current code unless you encounter real runtime errors.
- The main gap is documentation and benchmark result reporting, not the core offline comparison design.
