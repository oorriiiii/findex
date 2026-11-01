import pickle
import json
from pathlib import Path
from findex.index import InvertedIndex
from contextlib import contextmanager


def save_index_pickle(index: InvertedIndex, path: Path) -> None:
    """Зберігає індекс за допомогою pickle."""
    with open(path, "wb") as f:
        pickle.dump(index, f)


def load_index_pickle(path: Path) -> InvertedIndex:
    """Завантажує індекс за допомогою pickle."""
    with open(path, "rb") as f:
        return pickle.load(f)


# Додатковий формат на вибір (наприклад, JSON для метаданих і словника)
def save_index_json(index: InvertedIndex, path: Path) -> None:
    """Зберігає індекс у форматі JSON."""
    data = {
        "docs": {str(doc_id): {"doc_id": d.doc_id, "path": d.path, "length": d.length} for doc_id, d in
                 index.docs.items()},
        "index": {term: [{"doc_id": p.doc_id, "tf": p.tf} for p.postings] for term, postings in index.index.items()}
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_index_json(path: Path) -> InvertedIndex:
    """Завантажує індекс із формату JSON."""
    from findex.models import DocMeta, Posting
    from collections import defaultdict

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    idx = InvertedIndex()
    for doc_id_str, d in data["docs"].items():
        idx.docs[int(doc_id_str)] = DocMeta(doc_id=d["doc_id"], path=d["path"], length=d["length"])

    for term, postings in data["index"].items():
        idx.index[term] = [Posting(doc_id=p["doc_id"], tf=p["tf"]) for p in postings]

    return idx

@contextmanager
def open_index(path: Path):
    """Контекстний менеджер для безпечного завантаження та закриття індексу."""
    file_obj = open(path, "rb")
    try:
        index_data = pickle.load(file_obj)
        yield index_data
    finally:
        file_obj.close()