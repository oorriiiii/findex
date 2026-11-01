from dataclasses import dataclass, field
import math
from typing import Protocol, Sequence


@dataclass(order=True)
class SearchResult:
    score: float
    doc_id: int = field(compare=False)


class Scorer(Protocol):
    def score(self, term: str, index, doc_ids: Sequence[int]) -> dict[int, float]:
        ...


class TfIdf:
    def score(self, term: str, index, doc_ids: Sequence[int]) -> dict[int, float]:
        scores = {}
        df = index.df(term)
        if df == 0:
            return scores

        idf = math.log(index.num_docs / df)
        for doc_id in doc_ids:
            postings = index.get(term, [])
            tf = next((p.tf for p in postings if p.doc_id == doc_id), 0)
            scores[doc_id] = tf * idf
        return scores


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def score(self, term: str, index, doc_ids: Sequence[int]) -> dict[int, float]:
        scores = {}
        df = index.df(term)
        if df == 0:
            return scores

        # Захист від від'ємного/нульового підлогогарифмічного виразу
        idf = math.log((index.num_docs - df + 0.5) / (df + 0.5) + 1.0)
        avgdl = index.avg_doc_length if index.avg_doc_length > 0 else 1.0

        for doc_id in doc_ids:
            postings = index.get(term, [])
            tf = next((p.tf for p in postings if p.doc_id == doc_id), 0)

            doc_len = len(index._documents.get(doc_id, "").split()) if hasattr(index, "_documents") else avgdl

            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / avgdl))
            scores[doc_id] = idf * (numerator / denominator) if denominator > 0 else 0.0

        return scores