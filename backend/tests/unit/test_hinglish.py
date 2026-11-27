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


def test_word_fixes_match_when_registered_with_romanized_hinglish_text(tmp_path):
    from src.media.transcription import load_cached_transcript_data, register_word_fixes

    video_path = tmp_path / "hinglish.mp4"
    video_path.with_suffix(".transcript_cache.json").write_text(
        '{"version": 2, "words": [{"text": "मुझे", "start": 100, "end": 400}, '
        '{"text": "नहीं", "start": 450, "end": 800}], "utterances": []}',
        encoding="utf-8",
    )
    loaded = load_cached_transcript_data(video_path)
    assert [w["text"] for w in loaded["words"]] == ["mujhe", "nahi"]

    assert register_word_fixes(video_path, {(100, 400, "mujhe"): {"start": 0.15}})
    reloaded = load_cached_transcript_data(video_path)
    assert reloaded["words"][0]["start"] == 150
    assert reloaded["words"][0]["text"] == "mujhe"
