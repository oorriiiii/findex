from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Iterator, List, Optional


@dataclass
class Posting:
    doc_id: int
    tf: int = 1


@dataclass
class DocMeta:
    doc_id: int
    path: Path
    length: int = 0


class Index(Mapping[str, List[Posting]]):
    def __init__(
            self,
            postings: Optional[dict[str, List[Posting]]] = None,
            documents: Optional[dict[int, Any]] = None,
    ) -> None:
        self._postings: dict[str, List[Posting]] = postings if postings is not None else {}
        self._documents: dict[int, Any] = documents if documents is not None else {}

    @property
    def index(self) -> dict[str, List[Posting]]:
        """Аліас для сумісності зі сховищем та алгоритмами."""
        return self._postings

    @property
    def docs(self) -> dict[int, Any]:
        """Словник документів."""
        return self._documents

    def __getitem__(self, term: str) -> List[Posting]:
        return self._postings[term]

    def __iter__(self) -> Iterator[str]:
        return iter(self._postings)

    def __len__(self) -> int:
        return len(self._postings)

    @cached_property
    def num_docs(self) -> int:
        return len(self._documents)

    @cached_property
    def avg_doc_length(self) -> float:
        if not self._documents:
            return 0.0
        total_len = 0
        for doc in self._documents.values():
            if isinstance(doc, str):
                total_len += len(doc.split())
            else:
                total_len += 10  # fallback для метаданих
        return total_len / self.num_docs if self.num_docs > 0 else 0.0

    def df(self, term: str) -> int:
        return len(self._postings.get(term, []))

    def add_document(self, path: Path, text: str) -> int:
        """Додавання документа для підтримки тестів та побудови індексу."""
        doc_id = len(self._documents) + 1
        self._documents[doc_id] = text
        tokens = text.lower().split()

        token_counts: dict[str, int] = {}
        for token in tokens:
            token_counts[token] = token_counts.get(token, 0) + 1

        for token, tf in token_counts.items():
            if token not in self._postings:
                self._postings[token] = []
            self._postings[token].append(Posting(doc_id=doc_id, tf=tf))

        return doc_id

    def __repr__(self) -> str:
        return f"<Index documents={self.num_docs} terms={len(self)}>"