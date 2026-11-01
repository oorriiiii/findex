import urllib.request
from pathlib import Path

GUTENBERG_BOOKS = {
    "moby_dick": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
    "frankenstein": "https://www.gutenberg.org/cache/epub/84/pg84.txt",
    "sherlock": "https://www.gutenberg.org/cache/epub/1661/pg1661.txt",
    "pride_and_prejudice": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
    "war_and_peace": "https://www.gutenberg.org/cache/epub/2600/pg2600.txt",
}


def build_corpus(data_dir: Path, target_docs: int = 1000, target_mb: int = 50) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_texts = []

    print("Завантаження базових текстів з Project Gutenberg...")
    for name, url in GUTENBERG_BOOKS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                text = response.read().decode("utf-8", errors="ignore")
                raw_texts.append((name, text))
                print(f"  [+] Завантажено {name} ({len(text) / (1024 * 1024):.2f} MB)")
        except Exception as e:
            print(f"  [!] Помилка завантаження {name}: {e}")

    if not raw_texts:
        print("Не вдалося завантажити книги. Генеруємо синтетичний текст...")
        sample = (
                "System programming, neural networks, and state-of-the-art tokenizers "
                "don't load 50MB at once! UTF-8 café naïve résumé co-operate 2026.\n" * 500
        )
        raw_texts = [("synthetic", sample)]

    full_text = "\n\n".join(t for _, t in raw_texts)

    target_bytes = target_mb * 1024 * 1024
    bytes_per_doc = target_bytes // target_docs

    print(f"Формування {target_docs} документів (~{target_mb} МБ загалом) у {data_dir}...")
    for i in range(target_docs):
        start = (i * 1500) % max(1, len(full_text) - bytes_per_doc)
        chunk = full_text[start: start + bytes_per_doc]
        if len(chunk.encode("utf-8")) < bytes_per_doc:
            multiplier = (bytes_per_doc // max(1, len(chunk.encode("utf-8")))) + 1
            chunk = (chunk * multiplier)[:bytes_per_doc]

        doc_path = data_dir / f"doc_{i:04d}.txt"
        doc_path.write_text(f"Document ID: {i}\n\n{chunk}", encoding="utf-8")

    total_size = sum(f.stat().st_size for f in data_dir.glob("*.txt")) / (1024 * 1024)
    print(f"Готово! Створено {target_docs} файлів загальним розміром {total_size:.2f} МБ.")


if __name__ == "__main__":
    build_corpus(Path("data"), target_docs=1000, target_mb=50)