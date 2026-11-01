from dataclasses import dataclass
from typing import Union

@dataclass
class Term:
    value: str

    def evaluate(self, index):
        # Повертає множину doc_id, що містять термін
        postings = index.get(self.value, [])
        return {p.doc_id for p in postings}

@dataclass
class Phrase:
    terms: list[str]

    def evaluate(self, index):
        # Логіка для фразового пошуку з урахуванням позицій
        ...

@dataclass
class And:
    left: Union['Term', 'Phrase', 'And', 'Or', 'Not']
    right: Union['Term', 'Phrase', 'And', 'Or', 'Not']

    def evaluate(self, index):
        return self.left.evaluate(index) & self.right.evaluate(index)

@dataclass
class Or:
    left: Union['Term', 'Phrase', 'And', 'Or', 'Not']
    right: Union['Term', 'Phrase', 'And', 'Or', 'Not']

    def evaluate(self, index):
        return self.left.evaluate(index) | self.right.evaluate(index)

@dataclass
class Not:
    expr: Union['Term', 'Phrase', 'And', 'Or', 'Not']

    def evaluate(self, index):
        all_docs = set(index._documents.keys()) if hasattr(index, "_documents") else set()
        return all_docs - self.expr.evaluate(index)