from pathlib import Path
from types import GeneratorType

from findex.corpus import iter_documents
from findex.stats import compute_stats_eager, compute_stats_lazy
from findex.tokenizer import tokenize


def test_tokenize_is_generator():
    stream = tokenize("Hello world")
    assert isinstance(stream, GeneratorType)


def test_tokenize_unicode_normalization():
    text = "Café résumé ﬁnance NAÏVE"
    assert list(tokenize(text)) == ["café", "résumé", "finance", "naïve"]


def test_tokenize_apostrophes_and_hyphens():
    text = "Don't 'quote' state-of-the-art -- co-operate і комп’ютер!"
    assert list(tokenize(text)) == [
        "don't",
        "quote",
        "state-of-the-art",
        "co-operate",
        "і",
        "комп'ютер",
    ]


def test_tokenize_numbers_and_alphanumeric():
    text = "In 2026, model B850M ran at 3.5GHz with 100% load."
    assert list(tokenize(text)) == ["in", "2026", "model", "b850m", "ran", "at", "3", "5ghz", "with", "100", "load"]


def test_iter_documents_and_stats_equivalence(tmp_path: Path):
    (tmp_path / "doc1.txt").write_text("Hello world! Don't panic.", encoding="utf-8")
    (tmp_path / "doc2.md").write_text("Hello Python 2026 world.", encoding="utf-8")
    (tmp_path / "ignored.bin").write_bytes(b"\x00\x01\x02")

    docs = list(iter_documents(tmp_path))
    assert len(docs) == 2

    lazy = compute_stats_lazy(tmp_path)
    eager = compute_stats_eager(tmp_path)

    assert lazy.doc_count == eager.doc_count == 2
    assert lazy.token_count == eager.token_count == 8
    assert lazy.vocab_size == eager.vocab_size == 6
    assert dict(lazy.top_terms)["hello"] == 2
    assert dict(lazy.top_terms)["world"] == 2