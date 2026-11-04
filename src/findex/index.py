from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Any
from findex.models import DocMeta, Posting, Index


class InvertedIndex:
    """Клас інвертованого індексу з підтримкою побудови за потоком документів."""

    def __init__(self):
        self.index: Dict[str, List[Posting]] = defaultdict(list)
        self.docs: Dict[int, DocMeta] = {}

    def build(self, document_stream) -> None:
        """Будує індекс за один прохід по лінивому пайплайну."""
        for doc_id, path, tokens in document_stream:
            total_tokens = 0
            term_freqs = defaultdict(int)

            for token in tokens:
                term_freqs[token] += 1
                total_tokens += 1

            self.docs[doc_id] = DocMeta(doc_id=doc_id, path=path, length=total_tokens)

            for term, freq in term_freqs.items():
                self.index[term].append(Posting(doc_id=doc_id, tf=freq))


def build_partial(file_paths: Sequence[Path], start_doc_id: int) -> Index:
    """
    Будує частковий індекс (partial index) для заданого списку шляхів до файлів
    із початковим діапазоном doc_id. Функція є рівнем модуля для серіалізації через pickle.
    """
    partial_index = Index()
    current_id = start_doc_id

    for path in file_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        tokens = text.lower().split()
        total_tokens = len(tokens)

        # Реєструємо метадані документа
        partial_index.docs[current_id] = DocMeta(doc_id=current_id, path=path, length=total_tokens)

        # Рахуємо терм-частоти (TF) для конкретного документа
        term_freqs: Dict[str, int] = {}
        for token in tokens:
            term_freqs[token] = term_freqs.get(token, 0) + 1

        for term, tf in term_freqs.items():
            if term not in partial_index.index:
                partial_index.index[term] = []
            partial_index.index[term].append(Posting(doc_id=current_id, tf=tf))

        current_id += 1

    return partial_index


def merge(indices: Sequence[Index]) -> Index:
    """
    Послідовно об'єднує список часткових індексів (indices) у єдиний глобальний індекс.
    Гарантує унікальність та правильний зсув doc_id для всього корпусу.
    """
    merged_index = Index()
    global_doc_id_offset = 1

    for partial in indices:
        # Змінюємо мапінг документів із новим глобальним зсувом ID
        id_mapping: Dict[int, int] = {}

        for old_id, doc_meta in partial.docs.items():
            new_id = global_doc_id_offset
            id_mapping[old_id] = new_id
            # Оновлюємо внутрішній doc_id у метаданих
            merged_index.docs[new_id] = DocMeta(doc_id=new_id, path=doc_meta.path, length=doc_meta.length)
            global_doc_id_offset += 1

        # Об'єднуємо постинг-листи для кожного терміна з урахуванням нових ID
        for term, postings in partial.index.items():
            if term not in merged_index.index:
                merged_index.index[term] = []

            for p in postings:
                if p.doc_id in id_mapping:
                    adjusted_posting = Posting(doc_id=id_mapping[p.doc_id], tf=p.tf)
                    merged_index.index[term].append(adjusted_posting)

    return merged_index