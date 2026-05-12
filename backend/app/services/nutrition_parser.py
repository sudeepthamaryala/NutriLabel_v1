import re

from app.schemas.analyse import NutritionData


_NUMBER = r"([0-9]+(?:[\.,][0-9]+)?)"
_UNIT_G = r"\s*(?:g|gram|grams)?\b"
_UNIT_MG = r"\s*(?:mg|milligram|milligrams)?\b"


def parse(text: str) -> NutritionData:
    normalized = _normalize_text(text)
    ingredients = _extract_ingredients(normalized)

    return NutritionData(
        calories=_extract_number(
            normalized,
            [
                r"\b(?:energy|calories?|kcal)\b[^\d]{0,20}" + _NUMBER,
                _NUMBER + r"\s*(?:kcal|calories?)\b",
            ],
        ),
        total_fat_g=_extract_number(
            normalized,
            [
                r"\btotal\s+fat\b[^\d]{0,20}" + _NUMBER + _UNIT_G,
                r"\bfat\b[^\d]{0,20}" + _NUMBER + _UNIT_G,
            ],
        ),
        protein_g=_extract_number(normalized, [r"\bprotein\b[^\d]{0,20}" + _NUMBER + _UNIT_G]),
        sugar_g=_extract_number(
            normalized,
            [
                r"\btotal\s+sugars?\b[^\d]{0,20}" + _NUMBER + _UNIT_G,
                r"\bsugars?\b[^\d]{0,20}" + _NUMBER + _UNIT_G,
            ],
        ),
        sodium_mg=_extract_number(normalized, [r"\bsodium\b[^\d]{0,20}" + _NUMBER + _UNIT_MG]),
        serving_size=_extract_serving_size(normalized),
        ingredients=ingredients,
    )


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"(?i)\b[oO](?=\d)", "0", text)
    text = re.sub(r"(?i)(?<=\d)[oO]\b", "0", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def _extract_number(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def _extract_serving_size(text: str) -> str | None:
    match = re.search(
        r"\bserving\s+size\b\s*:?\s*([^\n;]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip()[:120]


def _extract_ingredients(text: str) -> list[str]:
    match = re.search(
        r"\bingredients?\b\s*:?\s*([^\n]+)",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return []

    raw = match.group(1)
    return [
        item.strip(" .;:").lower()
        for item in re.split(r",|;", raw)
        if item.strip(" .;:")
    ][:30]
