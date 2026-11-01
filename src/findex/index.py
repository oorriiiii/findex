from collections import defaultdict
from typing import Dict, List
from findex.models import DocMeta, Posting


class InvertedIndex:
    def __init__(self):
        # term -> list of Posting
        self.index: Dict[str, List[Posting]] = defaultdict(list)
        self.docs: Dict[int, DocMeta] = {}

    def build(self, document_stream):
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