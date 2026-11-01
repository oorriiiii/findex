from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

@dataclass(frozen=True, slots=True)
class Document:
    doc_id: str
    path: Path
    text: str


def iter_documents(
    corpus_dir: Path,
    extensions: tuple[str, ...] = (".txt", ".md")
) -> Iterator[Document]:
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Директорія корпусу не знайдена: {corpus_dir}")

    paths = sorted(
        p for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in extensions
    )

    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        doc_id = str(path.relative_to(corpus_dir))
        yield Document(doc_id=doc_id, path=path, text=text)


def load_documents_eager(
    corpus_dir: Path,
    extensions: tuple[str, ...] = (".txt", ".md")
) -> list[Document]:
    return list(iter_documents(corpus_dir, extensions=extensions))