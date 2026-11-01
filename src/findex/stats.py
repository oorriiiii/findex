from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from findex.corpus import iter_documents, load_documents_eager
from findex.tokenizer import tokenize, tokenize_eager


@dataclass
class CorpusStats:
    doc_count: int
    token_count: int
    vocab_size: int
    top_terms: list[tuple[str, int]]


def compute_stats_lazy(corpus_dir: Path, top_k: int = 50) -> CorpusStats:
    doc_count = 0
    token_count = 0
    term_counts: Counter[str] = Counter()

    for doc in iter_documents(corpus_dir):
        doc_count += 1
        for token in tokenize(doc.text):
            token_count += 1
            term_counts[token] += 1

    return CorpusStats(
        doc_count=doc_count,
        token_count=token_count,
        vocab_size=len(term_counts),
        top_terms=term_counts.most_common(top_k),
    )


def compute_stats_eager(corpus_dir: Path, top_k: int = 50) -> CorpusStats:
    docs = load_documents_eager(corpus_dir)
    all_tokens: list[str] = []

    for doc in docs:
        all_tokens.extend(tokenize_eager(doc.text))

    term_counts = Counter(all_tokens)

    return CorpusStats(
        doc_count=len(docs),
        token_count=len(all_tokens),
        vocab_size=len(term_counts),
        top_terms=term_counts.most_common(top_k),
    )