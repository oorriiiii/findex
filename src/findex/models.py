from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class DocMeta:
    doc_id: int
    path: str
    length: int  # загальна кількість токенів

@dataclass(frozen=True, slots=True)
class Posting:
    doc_id: int
    tf: int  # term frequency