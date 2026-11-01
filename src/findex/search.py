from typing import List, Set
from findex.index import InvertedIndex


class SearchEngine:
    def __init__(self, index: InvertedIndex, engine_type: str = "merge"):
        self.index = index
        self.engine_type = engine_type

    def search(self, terms: List[str]) -> List[int]:
        """Виконує пошук за списком термінів залежно від обраного двигуна."""
        if not terms:
            return []

        if self.engine_type == "merge":
            return self._search_merge(terms)
        elif self.engine_type == "set":
            return self._search_set(terms)
        else:
            raise ValueError(f"Unknown engine type: {self.engine_type}")

    def _search_merge(self, terms: List[str]) -> List[int]:
        """Двовказівниковий merge по відсортованих списках постінгів (AND для списку термінів)."""
        if not terms:
            return []

        # Отримуємо списки doc_id для кожного терміна (вони вже відсортовані за рахунок побудови)
        postings_lists = [
            [p.doc_id for p in self.index.index.get(term, [])]
            for term in terms
        ]

        if not postings_lists or not postings_lists[0]:
            return []

        # Починаємо з першого списку і послідовно робимо merge (AND) з іншими
        result = postings_lists[0]
        for other in postings_lists[1:]:
            result = self._merge_intersect(result, other)
            if not result:
                break
        return result

    @staticmethod
    def _merge_intersect(list1: List[int], list2: List[int]) -> List[int]:
        """Two-pointer перетин двох відсортованих списків doc_id."""
        i, j = 0, 0
        intersect = []
        while i < len(list1) and j < len(list2):
            if list1[i] == list2[j]:
                intersect.append(list1[i])
                i += 1
                j += 1
            elif list1[i] < list2[j]:
                i += 1
            else:
                j += 1
        return intersect

    def _search_set(self, terms: List[str]) -> List[int]:
        """Пошук через множини (set intersection)."""
        if not terms:
            return []

        sets = [
            set(p.doc_id for p in self.index.index.get(term, []))
            for term in terms
        ]

        if not sets[0]:
            return []

        result_set = sets[0]
        for s in sets[1:]:
            result_set = result_set.intersection(s)
            if not result_set:
                break

        return sorted(list(result_set))