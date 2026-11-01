from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
import pickle

class Index(Mapping):
    def __init__(self, postings: dict, documents: dict):
        self._postings = postings
        self._documents = documents

    def __getitem__(self, term: str):
        return self._postings[term]

    def __iter__(self):
        return iter(self._postings)

    def __len__(self):
        return len(self._postings)

    @cached_property
    def num_docs(self) -> int:
        return len(self._documents)

    @cached_property
    def avg_doc_length(self) -> float:
        if not self._documents:
            return 0.0
        total_len = sum(len(doc_text.split()) for doc_text in self._documents.values())
        return total_len / self.num_docs

    def df(self, term: str) -> int:
        return len(self._postings.get(term, []))

    def __repr__(self) -> classmethod:
        return f"<Index documents={self.num_docs} terms={len(self)}>"