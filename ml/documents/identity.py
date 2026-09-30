"""Identifier validation and conservative name comparison. Never log inputs."""
import re

_D = ((0,1,2,3,4,5,6,7,8,9),(1,2,3,4,0,6,7,8,9,5),(2,3,4,0,1,7,8,9,5,6),
      (3,4,0,1,2,8,9,5,6,7),(4,0,1,2,3,9,5,6,7,8),(5,9,8,7,6,0,4,3,2,1),
      (6,5,9,8,7,1,0,4,3,2),(7,6,5,9,8,2,1,0,4,3),(8,7,6,5,9,3,2,1,0,4),(9,8,7,6,5,4,3,2,1,0))
_P = ((0,1,2,3,4,5,6,7,8,9),(1,5,7,6,2,8,3,0,9,4),(5,8,0,3,7,9,6,1,4,2),
      (8,9,1,6,0,4,3,5,2,7),(9,4,5,3,1,2,6,8,7,0),(4,2,8,6,5,7,3,9,0,1),
      (2,7,9,3,8,0,6,4,1,5),(7,0,4,6,9,1,3,2,5,8))
AADHAAR = re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")


def verhoeff(number):
    number = re.sub(r"[ -]", "", number)
    if not re.fullmatch(r"[2-9]\d{11}", number):
        return False
    c = 0
    for i, digit in enumerate(reversed(number)):
        c = _D[c][_P[i % 8][int(digit)]]
    return c == 0


def mask_identifiers(text):
    return AADHAAR.sub(lambda m: "********" + re.sub(r"\D", "", m.group())[-4:], str(text))


def name_score(left, right):
    from rapidfuzz.fuzz import ratio
    def words(value):
        return [w for w in re.findall(r"[^\W\d_]+", value.casefold())
                if w not in {"mr", "mrs", "ms", "dr", "shri", "smt", "miss"}]
    a, b = words(left), words(right)
    if not a or not b:
        return 0.0
    if sorted(a) == sorted(b):
        return 100.0
    # Initials are compatible only with a complete matching other name token.
    if len(a) == len(b) and len(a) > 1 and set(a) & set(b):
        remaining = b.copy()
        for token in sorted(a, key=len, reverse=True):
            match = next((v for v in remaining if token == v or
                          (min(len(token), len(v)) == 1 and token[0] == v[0])), None)
            if match is None:
                break
            remaining.remove(match)
        else:
            return 94.0
    return float(ratio(" ".join(sorted(a)), " ".join(sorted(b))))
