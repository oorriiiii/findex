import time
from functools import wraps


def timed(func):
    """Декоратор для вимірювання часу виконання функції."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        print(f"[TIMED] Функція '{func.__name__}' виконалась за {end_time - start_time:.4f} секунд")
        return result

    return wrapper


def generate_snippet(text: str, term: str, window: int = 80) -> str:
    """Генерує сніпет тексту навколо знайденого терміна з підсвіткою."""
    lower_text = text.lower()
    lower_term = term.lower()
    pos = lower_text.find(lower_term)
    if pos == -1:
        return text[:window * 2] + "..."

    start = max(0, pos - window)
    end = min(len(text), pos + len(term) + window)

    snippet = text[start:end]
    highlighted = snippet.replace(term, f"**{term}**")
    return f"...{highlighted}..."