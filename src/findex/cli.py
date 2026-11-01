import argparse
import gc
import time
import tracemalloc
from pathlib import Path
from typing import Callable

from findex.stats import CorpusStats, compute_stats_eager, compute_stats_lazy


def benchmark(func: Callable[[Path], CorpusStats], corpus_dir: Path) -> tuple[CorpusStats, float, float]:
    gc.collect()
    tracemalloc.start()
    start_time = time.perf_counter()

    stats = func(corpus_dir)

    elapsed = time.perf_counter() - start_time
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak_bytes / (1024 * 1024)
    return stats, elapsed, peak_mb


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab 01: Corpus Statistics & Memory Benchmark")
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Шлях до директорії корпусу")
    args = parser.parse_args()

    print(f"Аналіз корпусу в директорії: {args.data_dir.resolve()}\n")

    print("1. Запуск ЛІНИВОГО (Generator / Lazy) конвеєра...")
    lazy_stats, lazy_time, lazy_peak = benchmark(compute_stats_lazy, args.data_dir)

    print("2. Запуск ЖАДІБНОГО (List / Eager) конвеєра...")
    eager_stats, eager_time, eager_peak = benchmark(compute_stats_eager, args.data_dir)

    print("\n" + "=" * 60)
    print("СТАТИСТИКА КОРПУСУ")
    print("=" * 60)
    print(f"Кількість документів : {lazy_stats.doc_count:,}")
    print(f"Загальна к-сть токенів: {lazy_stats.token_count:,}")
    print(f"Розмір словника       : {lazy_stats.vocab_size:,} унікальних термів")

    print("\n" + "=" * 60)
    print("ТАБЛИЦЯ ДЛЯ README.md (Lazy vs Eager)")
    print("=" * 60)
    print("| Метрика | Лінивий конвеєр (Generators) | Жадібний підхід (Lists) | Різниця |")
    print("|---|---|---|---|")
    print(f"| Кількість документів | {lazy_stats.doc_count:,} | {eager_stats.doc_count:,} | однаково |")
    print(f"| Загальна к-сть токенів | {lazy_stats.token_count:,} | {eager_stats.token_count:,} | однаково |")
    print(f"| Розмір словника | {lazy_stats.vocab_size:,} | {eager_stats.vocab_size:,} | однаково |")
    print(f"| Час виконання (с) | {lazy_time:.2f} s | {eager_time:.2f} s | {eager_time / max(lazy_time, 1e-6):.2f}x |")
    print(f"| Пікова пам'ять (МБ) | **{lazy_peak:.2f} MB** | **{eager_peak:.2f} MB** | **{eager_peak / max(lazy_peak, 1e-6):.1f}x більше** |")

    print("\nТоп-50 найчастотніших термів:")
    for rank, (term, count) in enumerate(lazy_stats.top_terms, start=1):
        print(f"{rank:2d}. {term:<18} — {count:,}")


if __name__ == "__main__":
    main()