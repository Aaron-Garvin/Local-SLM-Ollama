import json
import time
import requests
import statistics
import threading
import psutil
import platform
import ctypes
import os
import re

# Platform-dependent CPU name extraction
def get_cpu_name():
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return name.strip()
        except Exception:
            return platform.processor()
    else:
        # Fallback for Linux/macOS
        try:
            import subprocess
            if platform.system() == "Darwin":
                return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
            elif platform.system() == "Linux":
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            return line.split(":")[1].strip()
        except Exception:
            pass
        return platform.processor()

# Platform-dependent Total RAM extraction
def get_total_ram():
    if platform.system() == "Windows":
        try:
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            return 0.0
    else:
        try:
            total = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            return round(total / (1024 ** 3), 1)
        except Exception:
            return 0.0

# Memory monitoring for Ollama processes
current_peak_ram = 0
monitor_active = False

def memory_monitor_thread():
    global current_peak_ram, monitor_active
    while monitor_active:
        try:
            total_mem = 0
            for proc in psutil.process_iter(['name', 'memory_info']):
                try:
                    name = proc.info['name'].lower()
                    if 'ollama' in name:
                        total_mem += proc.info['memory_info'].rss
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            if total_mem > current_peak_ram:
                current_peak_ram = total_mem
        except Exception:
            pass
        time.sleep(0.1)

# Main script logic
MODELS = ["mistral", "llama3.2", "phi3:mini"]

with open("benchmark_prompts/prompts.json") as f:
    prompts = json.load(f)

results = {m: {"latencies": [], "successes": 0, "total": 0, "peak_ram": 0.0} for m in MODELS}

timeout_seconds = 120
max_retries = 2

# Start background memory monitor thread
monitor_active = True
monitor_t = threading.Thread(target=memory_monitor_thread, daemon=True)
monitor_t.start()

print("Gathering host system specifications...")
hardware = {
    "cpu": get_cpu_name(),
    "ram_total_gb": get_total_ram(),
    "os": f"{platform.system()} {platform.release()}"
}

print(f"Host CPU: {hardware['cpu']}")
print(f"Host OS: {hardware['os']}")
print(f"Host RAM: {hardware['ram_total_gb']} GB")

for model in MODELS:
    print(f"\n=== Benchmarking {model} ===")
    current_peak_ram = 0 # reset peak RAM tracking for this model
    
    for i, p in enumerate(prompts):
        print(f" Prompt {i+1}/{len(prompts)}", end="", flush=True)
        results[model]["total"] += 1
        attempt_success = False
        final_reason = None
        
        for attempt in range(1, max_retries + 1):
            start = time.time()
            try:
                r = requests.post(
                    "http://localhost:8000/extract",
                    json={"text": p["text"], "model": model},
                    timeout=timeout_seconds,
                )
                latency = time.time() - start
                if r.status_code == 200:
                    results[model]["latencies"].append(latency)
                    results[model]["successes"] += 1
                    print(f" OK ({latency:.1f}s)")
                    attempt_success = True
                    break
                else:
                    final_reason = f"HTTP {r.status_code}"
            except Exception as e:
                latency = timeout_seconds
                final_reason = f"Error: {e}"

        if not attempt_success:
            results[model]["latencies"].append(timeout_seconds)
            print(f" FAIL ({final_reason})")
            
    # Record the peak RAM consumption of Ollama for this model (convert bytes to GB)
    results[model]["peak_ram"] = round(current_peak_ram / (1024 ** 3), 1)

# Stop the memory monitor
monitor_active = False

# Compute summary stats and generate console report
print("\n" + "=" * 80)
print("LOCAL SLM INFERENCE BENCHMARK REPORT")
print("=" * 80)
print(f"System: {hardware['cpu']} | {hardware['os']} | {hardware['ram_total_gb']}GB RAM")
print("-" * 80)
print(f'{"Model":<15} {"Avg Latency":<14} {"Median":<10} {"Success %":<11} {"Peak RAM"}')
print("-" * 80)

summary_stats = {}
for model in MODELS:
    lats = results[model]["latencies"]
    success_pct = 0
    if results[model]["total"] > 0:
        success_pct = 100 * results[model]["successes"] / results[model]["total"]
    avg = statistics.mean(lats) if lats else float("nan")
    med = statistics.median(lats) if lats else float("nan")
    peak_ram = results[model]["peak_ram"]
    
    print(
        f"{model:<15} {avg:<14.2f} "
        f"{med:<10.2f} {success_pct:<11.0f}% {peak_ram:.1f} GB"
    )
    
    summary_stats[model] = {
        "avg": avg,
        "median": med,
        "success_pct": success_pct,
        "peak_ram": peak_ram
    }

# Generate recommendations
model_display_names = {
    "mistral": "Mistral 7B",
    "llama3.2": "Llama 3.2 3B",
    "phi3:mini": "Phi-3 Mini"
}

# Best Quality
sorted_by_quality = sorted(MODELS, key=lambda m: (summary_stats[m]['success_pct'], -summary_stats[m]['avg']), reverse=True)
best_quality = model_display_names[sorted_by_quality[0]]

# Fastest
valid_speed = [m for m in MODELS if summary_stats[m]['success_pct'] > 0]
fastest = model_display_names[sorted(valid_speed, key=lambda m: summary_stats[m]['avg'])[0]] if valid_speed else "N/A"

# Best Low RAM
best_low_ram = "Llama 3.2 3B"
if summary_stats["phi3:mini"]['peak_ram'] < summary_stats["llama3.2"]['peak_ram'] and summary_stats["phi3:mini"]['peak_ram'] > 0:
    best_low_ram = "Phi-3 Mini"

# Best Balance
if summary_stats["llama3.2"]['success_pct'] >= 90:
    best_balance = "Llama 3.2 3B (Extremely fast response time, low memory footprint, and high schema success)"
elif summary_stats["mistral"]['success_pct'] > summary_stats["llama3.2"]['success_pct'] + 15:
    best_balance = "Mistral 7B (Higher schema extraction success warrants the memory/latency overhead)"
else:
    best_balance = "Llama 3.2 3B (Fastest execution speed and lightweight memory requirement)"

recommendations = {
    "best_quality": best_quality,
    "fastest": fastest,
    "best_low_ram": best_low_ram,
    "best_balance": best_balance
}

print("-" * 80)
print("MODEL CHOICE RECOMMENDATIONS")
print("-" * 80)
print(f"- Best Quality: {best_quality}")
print(f"- Fastest: {fastest}")
print(f"- Best for RAM < 8GB: {best_low_ram}")
print(f"- Best Overall Balance: {best_balance}")
print("=" * 80)

# Save results to benchmark_results.json
with open("benchmark_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Detailed logs saved to benchmark_results.json")

# Overwrite README.md results sections
try:
    with open("README.md", "r", encoding="utf-8") as f:
        readme_content = f.read()

    # Update hardware specs
    readme_content = readme_content.replace("- Machine: `[Your laptop/PC model, e.g., Dell XPS 15 / MacBook Pro M2]`", f"- Machine: `{hardware['cpu']}`")
    readme_content = readme_content.replace("- RAM: `[e.g., 16GB RAM / 32GB RAM]`", f"- RAM: `{hardware['ram_total_gb']}GB RAM`")
    readme_content = readme_content.replace("- OS: `[e.g., Windows 11 / Ubuntu 22.04]`", f"- OS: `{hardware['os']}`")

    # Construct the Markdown table
    table_lines = [
        "| Model        | Avg Latency | Median | JSON Success | Peak RAM |",
        "|--------------|-------------|--------|--------------|----------|"
    ]
    for m in ["mistral", "llama3.2", "phi3:mini"]:
        stats = summary_stats[m]
        display = model_display_names[m]
        avg = f"`{stats['avg']:.2f}s`" if not statistics.math.isnan(stats['avg']) else "`N/A`"
        med = f"`{stats['median']:.2f}s`" if not statistics.math.isnan(stats['median']) else "`N/A`"
        succ = f"`{stats['success_pct']:.0f}%`"
        ram = f"`{stats['peak_ram']:.1f}GB`"
        table_lines.append(f"| {display:<12} | {avg:<11} | {med:<6} | {succ:<12} | {ram:<8} |")
    
    table_content = "\n".join(table_lines)

    # Construct Recommendations Guide
    guide_content = (
        f"- **Best Quality**: {best_quality}\n"
        f"- **Fastest**: {fastest}\n"
        f"- **Best for RAM < 8GB**: {best_low_ram}\n"
        f"- **Best Overall Balance**: {best_balance}"
    )

    # Find the position of the Benchmark Results section
    start_idx = readme_content.find("## Benchmark Results")
    end_idx = readme_content.find("---", start_idx)
    
    if start_idx != -1 and end_idx != -1:
        new_results_section = (
            "## Benchmark Results\n"
            "*Note: Run `python benchmark.py` to fill out these values based on your local run. Below is a template table:*\n\n"
            f"{table_content}\n\n"
            "## Model Choice Guide\n"
            f"{guide_content}\n\n"
        )
        readme_content = readme_content[:start_idx] + new_results_section + readme_content[end_idx:]

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("README.md updated successfully with benchmark results.")
except Exception as e:
    print(f"Warning: Failed to auto-update README.md: {e}")

