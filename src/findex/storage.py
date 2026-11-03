from pathlib import Path
import pickle
from contextlib import contextmanager
from typing import Iterator, Any

@contextmanager
def open_index(path: Path) -> Iterator[Any]:
    """Контекстний менеджер для безпечного завантаження індексу."""
    index = load_index(path)
    try:
        yield index
    finally:
        pass

def save_index(index: object, path: Path) -> None:
    """Зберігає індекс у файл за допомогою pickle."""
    with open(path, "wb") as f:
        pickle.dump(index, f)

def load_index(path: Path) -> object:
    """Завантажує індекс із файлу pickle."""
    with open(path, "rb") as f:
        return pickle.load(f)