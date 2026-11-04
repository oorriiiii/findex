from pathlib import Path
from findex.index import build_partial, merge
from findex.models import Index

def test_parallel_equivalence(tmp_path: Path):
    # Створюємо кілька тестових файлів
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "doc1.py").write_text("hello python world async", encoding="utf-8")
    (d / "doc2.py").write_text("python concurrency and threads", encoding="utf-8")
    (d / "doc3.py").write_text("gil and python processes", encoding="utf-8")

    files = sorted(list(d.glob("*.py")))

    # Послідовна збірка через один partial
    index_serial = build_partial(files, start_doc_id=1)

    # Паралельна/розбита збірка (наприклад, два чанки)
    part1 = build_partial(files[:2], start_doc_id=1)
    part2 = build_partial(files[2:], start_doc_id=3)
    index_merged = merge([part1, part2])

    # Перевіряємо, що кількість документів і термінів збігаються
    assert index_serial.num_docs == index_merged.num_docs
    assert set(index_serial.index.keys()) == set(index_merged.index.keys())