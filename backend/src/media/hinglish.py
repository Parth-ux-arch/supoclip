"""Latin-script display of Hindi speech without changing word timings."""

import re

VOWELS = dict(zip("अआइईउऊऋएऐओऔ", ("a", "aa", "i", "ee", "u", "oo", "ri", "e", "ai", "o", "au")))
MATRAS = dict(zip("ािीुूृेैोौ", ("a", "i", "i", "u", "u", "ri", "e", "ai", "o", "au")))
CONSONANTS = dict(zip(
    "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ",
    ("k", "kh", "g", "gh", "ng", "ch", "chh", "j", "jh", "ny", "t", "th", "d", "dh", "n", "t", "th", "d", "dh", "n", "p", "ph", "b", "bh", "m", "y", "r", "l", "v", "sh", "sh", "s", "h", "l"),
))
CONSONANTS.update({"क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "य़": "y"})
MARKS = {"ं": "n", "ँ": "n", "ः": "h", "़": "", "ॅ": "e", "ॉ": "o", "।": ".", "॥": "."}
DIGITS = dict(zip("०१२३४५६७८९", "0123456789"))
COMMON = {
    "मैं": "main", "हूँ": "hoon", "है": "hai", "हैं": "hain", "नहीं": "nahi",
    "मुझे": "mujhe", "तुम्हें": "tumhe", "आप": "aap", "क्या": "kya",
    "क्यों": "kyun", "यह": "yeh", "वह": "woh", "और": "aur", "करना": "karna",
    "करते": "karte", "करती": "karti", "बहुत": "bahut", "अच्छा": "achha",
    "अच्छी": "achhi", "कोई": "koi", "गया": "gaya", "गई": "gayi",
    "में": "mein", "बात": "baat", "काम": "kaam", "हम": "hum", "कहां": "kahan",
    "कहाँ": "kahan", "वीडियो": "video", "बिजनेस": "business", "शेयर": "share",
    "लाइक": "like", "सब्सक्राइब": "subscribe", "चाहिए": "chahiye",
    "बहुत": "bahut", "साथ": "saath", "नमस्ते": "namaste", "हिंदी": "hindi",
}
DEVANAGARI = re.compile(r"[\u0900-\u097f]+")


def _romanize_token(token: str) -> str:
    if token in COMMON:
        return COMMON[token]
    out = ""
    chars = list(token)
    for index, char in enumerate(chars):
        if char in CONSONANTS:
            next_char = chars[index + 1] if index + 1 < len(chars) else ""
            # The implicit vowel is absent at a word end and before a halant.
            next_has_matra = (
                index > 0
                and next_char in CONSONANTS
                and index + 2 < len(chars)
                and chars[index + 2] in MATRAS
            )
            vowel = "" if next_char == "्" or not next_char or next_has_matra else "a"
            if next_char in MATRAS:
                vowel = ""
            out += CONSONANTS[char] + vowel
        elif char in VOWELS:
            out += VOWELS[char]
        elif char in MATRAS:
            out += MATRAS[char]
        elif char == "्":
            continue
        elif char in MARKS:
            out += MARKS[char]
        elif char in DIGITS:
            out += DIGITS[char]
        elif "\u0900" <= char <= "\u097f":
            # A rare combining mark must not leak native script into a caption.
            continue
        else:
            out += char
    return out


def romanize_hindi(text: str) -> str:
    """Convert Devanagari runs; leave English and punctuation untouched."""
    return DEVANAGARI.sub(lambda match: _romanize_token(match.group()), text)
