import re
import unicodedata
from typing import Iterator

TOKEN_PATTERN = re.compile(
    r"[a-z0-9à-öø-ÿа-яіїєґ]+(?:['’\-][a-z0-9à-öø-ÿа-яіїєґ]+)*",
    re.IGNORECASE | re.UNICODE,
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("’", "'").replace("`", "'")
    return normalized.casefold()


def tokenize(text: str) -> Iterator[str]:
    normalized = normalize_text(text)
    for match in TOKEN_PATTERN.finditer(normalized):
        yield match.group(0)


def tokenize_eager(text: str) -> list[str]:
    normalized = normalize_text(text)
    return TOKEN_PATTERN.findall(normalized)