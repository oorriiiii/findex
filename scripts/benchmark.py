import os
import time
import statistics
import psutil
from pathlib import Path
import matplotlib.pyplot as plt

from findex.index import build_partial, merge
from findex.models import Index


def measure_run(data_dir: Path, workers: int, executor: str):
    files = sorted(list(data_dir.glob("**/*.txt")))
    chunk_size = max(1, len(files) // workers)
    chunks = []
    current_id = 1
    for i in range(0, len(files), chunk_size):
        chunk_files = files[i:i + chunk_size]
        if chunk_files:
            chunks.append((chunk_files, current_id))
            current_id += len(chunk_files)

    process = psutil.Process(os.getpid())

    # Вимірюємо початковий RSS та CPU часи
    mem_before = process.memory_info().rss
    cpu_start = process.cpu_times()
    start_wall = time.perf_counter()

    partial_indices = []
    if executor == "threads":
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(build_partial, cf, sid) for cf, sid in chunks]
            for f in as_completed(futures):
                partial_indices.append(f.result())
    elif executor == "processes":
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(build_partial, cf, sid) for cf, sid in chunks]
            for f in as_completed(futures):
                partial_indices.append(f.result())
    else:  # serial
        for cf, sid in chunks:
            partial_indices.append(build_partial(cf, sid))

    # Час злиття (merge)
    merge_start = time.perf_counter()
    _ = merge(partial_indices)
    merge_time = time.perf_counter() - merge_start

    wall_time = time.perf_counter() - start_wall
    cpu_end = process.cpu_times()
    cpu_time = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
    mem_peak = process.memory_info().rss

    return wall_time, cpu_time, mem_peak, merge_time


def run_benchmarks():
    data_dir = Path("data")
    cpu_count = os.cpu_count() or 4
    worker_list = [1, 2, 4, 8, cpu_count]
    worker_list = sorted(list(set(worker_list)))  # унікальні значення

    results = {}

    for executor in ["threads", "processes"]:
        results[executor] = []
        print(f"\n--- Екзекутор: {executor} ---")
        for w in worker_list:
            walls, cpus, mems, merges = [], [], [], []
            # Проганяємо 3 рази для медіани
            for _ in range(3):
                w_t, c_t, m_p, m_t = measure_run(data_dir, w, executor)
                walls.append(w_t)
                cpus.append(c_t)
                mems.append(m_p)
                merges.append(m_t)

            med_wall = statistics.median(walls)
            med_cpu = statistics.median(cpus)
            med_mem = statistics.median(mems) / (1024 * 1024)  # в MB
            med_merge = statistics.median(merges)

            results[executor].append({
                "workers": w,
                "wall": med_wall,
                "cpu": med_cpu,
                "mem": med_mem,
                "merge": med_merge
            })
            print(
                f"Workers: {w} | Wall: {med_wall:.4f}s | CPU: {med_cpu:.4f}s | RAM: {med_mem:.2f}MB | Merge: {med_merge:.4f}s")

    # Базовий час для розрахунку прискорення (processes з 1 воркером або serial)
    base_wall = results["processes"][0]["wall"]

    workers_x = [r["workers"] for r in results["processes"]]
    speedups = [base_wall / r["wall"] for r in results["processes"]]

    # Побудова графіка
    plt.figure(figsize=(8, 5))
    plt.plot(workers_x, speedups, marker='o', label='Реальне прискорення (Processes)', color='blue')
    plt.plot(workers_x, workers_x, linestyle='--', color='gray', label='Ідеальне лінійне прискорення')
    plt.xlabel('Кількість воркерів (N)')
    plt.ylabel('Прискорення (Speedup)')
    plt.title('Графік прискорення збірки індексу (ProcessPoolExecutor)')
    plt.legend()
    plt.grid(True)
    plt.savefig('speedup_chart.png', dpi=300)
    print("\nГрафік збережено у файл 'speedup_chart.png'!")


if __name__ == "__main__":
    run_benchmarks()