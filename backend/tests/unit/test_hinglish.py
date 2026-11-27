from src.media.hinglish import romanize_hindi


def test_hindi_caption_uses_latin_script():
    assert romanize_hindi("मुझे नहीं पता") == "mujhe nahi pata"


def test_mixed_caption_preserves_english_words():
    assert romanize_hindi("मैं हिंदी और English बोलता हूँ") == "main hindi aur English bolta hoon"


def test_english_caption_is_unchanged():
    assert romanize_hindi("This is English!") == "This is English!"


def test_common_hindi_and_english_loanwords_are_readable():
    assert romanize_hindi("आज हम बिजनेस की बात करेंगे") == "aaj hum business ki baat karenge"


def test_digits_and_nukta_letters_do_not_leave_devanagari_in_captions():
    rendered = romanize_hindi("फ़िल्म २०२६ में")
    assert rendered == "film 2026 mein"
    assert not any("\u0900" <= char <= "\u097f" for char in rendered)
