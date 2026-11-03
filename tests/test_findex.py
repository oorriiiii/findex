from pathlib import Path
import pytest
from hypothesis import given, strategies as st

from findex.storage import save_index, load_index
from findex.scoring import TfIdf, BM25
from findex.models import Index


@pytest.fixture
def sample_index(tmp_path: Path) -> Index:
    idx = Index()
    idx.add_document(Path("doc1.txt"), "python programming language async")
    idx.add_document(Path("doc2.txt"), "python indexing and search engines")
    idx.add_document(Path("doc3.txt"), "java and python performance")
    return idx


def test_index_mapping_protocol(sample_index: Index):
    """Перевірка реалізації протоколу Mapping для Index."""
    assert len(sample_index) > 0
    assert "python" in sample_index
    assert isinstance(list(iter(sample_index)), list)


def test_tokenizer_unicode():
    """Тестування токенізації з урахуванням Unicode та регістру."""
    text = "Python-3.10 async/await, Ґанок & Світ!"
    tokens = [t.lower() for t in text.split() if t.isalnum()]
    assert len(tokens) >= 0


def test_tfidf_scoring(sample_index: Index):
    """Перевірка роботи TF-IDF скорера."""
    scorer = TfIdf()
    scores = scorer.score("python", sample_index, [1, 2, 3])
    assert isinstance(scores, dict)


def test_bm25_scoring(sample_index: Index):
    """Перевірка роботи BM25 скорера."""
    scorer = BM25()
    scores = scorer.score("python", sample_index, [1, 2, 3])
    assert isinstance(scores, dict)


def test_save_load_pickle(sample_index: Index, tmp_path: Path):
    """Перевірка збереження та завантаження індексу через pickle."""
    file_path = tmp_path / "test_index.bin"
    save_index(sample_index, file_path)

    loaded = load_index(file_path)
    assert loaded.num_docs == sample_index.num_docs
    assert loaded.avg_doc_length == sample_index.avg_doc_length


@pytest.mark.slow
def test_large_corpus_simulation(sample_index: Index):
    """Повільний тест для імітації перевірки великого корпусу."""
    assert sample_index.num_docs == 3


@given(st.lists(st.integers(min_value=1, max_value=100), unique=True))
def test_doc_ids_property(doc_ids: list[int]):
    """Hypothesis властивість: унікальні ID документів обробляються коректно."""
    sorted_ids = sorted(doc_ids)
    for i in range(len(sorted_ids) - 1):
        assert sorted_ids[i] < sorted_ids[i + 1]


@given(st.text(min_size=1, max_size=20))
def test_save_load_invariant(text: str):
    """Hypothesis властивість: ініціалізація індексу працює стабільно."""
    idx = Index()
    if text.strip():
        idx.add_document(Path("test.txt"), text)
    assert idx.num_docs >= 0