import argparse
import time
import tracemalloc
from pathlib import Path
from findex.index import InvertedIndex
from findex.storage import save_index_pickle, load_index_pickle, save_index_json, load_index_json
from findex.search import SearchEngine


# Умовно імпортуємо твій лінивий пайплайн із Лаби 1 (залежно від того, як він у тебе названий)
# Наприклад: from findex.pipeline import process_corpus

def main():
    parser = argparse.ArgumentParser(description="Findex Search Engine CLI (Lab 2)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Команда побудови індексу
    parser_index = subparsers.add_parser("index", help="Build and save inverted index")
    parser_index.add_argument("corpus_dir", type=Path, help="Path to corpus directory")
    parser_index.add_argument("--out", type=Path, required=True, help="Output index file path")
    parser_index.add_argument("--format", choices=["pickle", "json"], default="pickle", help="Serialization format")

    # Команда пошуку
    parser_search = subparsers.add_parser("search", help="Search in saved inverted index")
    parser_search.add_argument("index_file", type=Path, help="Path to index file")
    parser_search.add_argument("query", type=str, help="Search query terms separated by space")
    parser_search.add_argument("--engine", choices=["merge", "set"], default="merge", help="Search engine algorithm")

    args = parser.parse_args()

    tracemalloc.start()
    start_time = time.perf_counter()

    if args.command == "index":
        print(f"Будуємо індекс з корпусу: {args.corpus_dir}...")

        # Т тут викликається твій генератор документів з Лаби 1
        # Наприклад: corpus_stream = process_corpus(args.corpus_dir)

        index = InvertedIndex()
        # index.build(corpus_stream)  # розкоментуй, коли підключиш свій потік з Лаби 1

        print(f"Зберігаємо індекс у {args.out} (формат: {args.format})...")
        if args.format == "pickle":
            save_index_pickle(index, args.out)
        else:
            save_index_json(index, args.out)

    elif args.command == "search":
        print(f"Завантажуємо індекс з {args.index_file}...")
        if args.index_file.suffix == ".json":
            index = load_index_json(args.index_file)
        else:
            index = load_index_pickle(args.index_file)

        terms = args.query.lower().split()
        print(f"Виконуємо пошук для термінів {terms} через двигун '{args.engine}'...")

        engine = SearchEngine(index, engine_type=args.engine)
        results = engine.search(terms)

        print(f"\nЗнайдено документів: {len(results)}")
        for doc_id in results[:10]:  # покажемо перші 10 результатів
            meta = index.docs.get(doc_id)
            if meta:
                print(f"  - Doc ID: {doc_id}, Path: {meta.path}")

    current, peak = tracemalloc.get_tracemalloc_memory()
    elapsed = time.perf_counter() - start_time
    tracemalloc.stop()

    print(f"\n--- Статистика виконання ---")
    print(f"Час виконання: {elapsed:.4f} сек.")
    print(f"Пікове споживання пам'яті: {peak / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    main()