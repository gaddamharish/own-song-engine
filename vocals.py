import math
import random

# Original, lightweight source-filter-inspired singing synthesis.
# This is deliberately procedural: no pretrained voice model or external API.

TELUGU_VOWELS = {
    "అ": "a", "ఆ": "aa", "ఇ": "i", "ఈ": "ii", "ఉ": "u", "ఊ": "uu",
    "ఋ": "u", "ఎ": "e", "ఏ": "ee", "ఐ": "ai", "ఒ": "o", "ఓ": "oo", "ఔ": "au",
    "ా": "aa", "ి": "i", "ీ": "ii", "ు": "u", "ూ": "uu", "ృ": "u",
    "ె": "e", "ే": "ee", "ై": "ai", "ొ": "o", "ో": "oo", "ౌ": "au", "ం": "m",
    "ః": "h", "్": "",
}
LATIN_VOWELS = set("aeiouy")

# Approximate first three formants (Hz); values are artistic synthesis targets.
FORMANTS = {
    "a": (800, 1150, 2900), "aa": (750, 1200, 2800),
    "i": (300, 2200, 3000), "ii": (280, 2300, 3100),
    "u": (350, 900, 2200), "uu": (320, 850, 2200),
    "e": (500, 1900, 2600), "ee": (450, 2000, 2700),
    "o": (500, 1000, 2500), "oo": (450, 950, 2400),
    "ai": (550, 1700, 2700), "au": (650, 1100, 2600),
    "m": (250, 900, 2100), "h": (700, 1400, 2600),
}
VOICE = {
    "Male": {"base": 115, "formant": 0.92, "breath": 0.025, "vibrato": 4.2},
    "Female": {"base": 205, "formant": 1.08, "breath": 0.018, "vibrato": 5.3},
    "Child": {"base": 285, "formant": 1.18, "breath": 0.012, "vibrato": 5.8},
}

def _syllables(text, language):
    """Return approximate vowel-centred lyric units, preserving Telugu vowel marks."""
    units = []
    is_telugu = language in ("Telugu", "Telugu-English") and any("\u0c00" <= c <= "\u0c7f" for c in text)
    if is_telugu:
        current = ""
        for ch in text:
            if ch.isspace() or ch in ",.!?;:\n":
                if current:
                    units.append(current); current = ""
                continue
            current += ch
            if ch in "అఆఇఈఉఊఋఎఏఐఒఓఔాిీుూృెేైొోౌం":
                units.append(current); current = ""
        if current:
            units.append(current)
        return units or ["ఆ"]
    # Simple vowel-group syllabification for Latin-script English / transliterated Telugu.
    word = ""
    for ch in text.lower():
        if ch.isalpha() or ch in "'-":
            word += ch
        elif word:
            units.extend(_split_word(word)); word = ""
    if word:
        units.extend(_split_word(word))
    return units or ["la", "la", "la"]

def _split_word(word):
    out, start, seen_vowel = [], 0, False
    for i, ch in enumerate(word):
        vowel = ch in LATIN_VOWELS
        if vowel and not seen_vowel:
            seen_vowel = True
        elif vowel and seen_vowel:
            # Consecutive vowels form a single diphthong group.
            continue
        elif not vowel and seen_vowel:
            out.append(word[start:i]); start = i; seen_vowel = False
    if start < len(word):
        out.append(word[start:])
    return out or [word]

def _vowel_for(unit):
    for ch in unit:
        if ch in TELUGU_VOWELS:
            v = TELUGU_VOWELS[ch]
            if v:
                return v
    low = unit.lower()
    for i, ch in enumerate(low):
        if ch in LATIN_VOWELS:
            if i + 1 < len(low) and low[i:i+2] in ("ai", "ay"):
                return "ai"
            if i + 1 < len(low) and low[i:i+2] in ("oo", "ou"):
                return "oo"
            if i + 1 < len(low) and low[i:i+2] in ("ee", "ea"):
                return "ee"
            if ch == "a": return "aa"
            if ch == "i": return "ii"
            if ch == "u": return "uu"
            if ch == "e": return "ee"
            if ch == "o": return "oo"
    return "a"

def synthesize_vocal(audio, sample_rate, duration, bpm, lyrics, language, voice, seed=7):
    if not lyrics or not lyrics.strip():
        return {"syllables": 0, "voice": voice}
    profile = VOICE.get(voice, VOICE["Female"])
    units = _syllables(lyrics.strip(), language)
    beat = 60.0 / bpm
    rng = random.Random(seed + 91)
    # Phrase timing leaves small gaps for breath and uses a simple rising/falling contour.
    phrase_slots = max(1, int(duration / max(beat * 0.42, 0.12)))
    if len(units) > phrase_slots:
        # Compress units evenly rather than truncating user lyrics.
        step = len(units) / phrase_slots
        units = [units[min(len(units)-1, int(i*step))] for i in range(phrase_slots)]
    slot = duration / max(1, len(units))
    base_midi = 48 if voice == "Male" else (55 if voice == "Female" else 60)
    scale = [0, 2, 4, 7, 9, 12]
    for idx, unit in enumerate(units):
        start = idx * slot + slot * 0.035
        dur = max(0.07, slot * (0.82 if unit[-1:] not in ",.!?" else 0.62))
        end = min(len(audio), int((start + dur) * sample_rate))
        begin = min(len(audio), int(start * sample_rate))
        if end <= begin:
            continue
        vowel = _vowel_for(unit)
        f1, f2, f3 = FORMANTS.get(vowel, FORMANTS["a"])
        formant_scale = profile["formant"]
        f1 *= formant_scale; f2 *= formant_scale; f3 *= formant_scale
        midi = base_midi + scale[(idx + rng.randrange(0, 2)) % len(scale)] + (12 if idx % 7 == 5 else 0)
        fundamental = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        amp = 0.15 if voice == "Male" else (0.12 if voice == "Female" else 0.095)
        for i in range(begin, end):
            t = (i - begin) / sample_rate
            rel = t / max(dur, 1e-5)
            attack = min(1.0, rel * 12.0)
            release = min(1.0, max(0.0, (1.0-rel) * 8.0))
            env = attack * release
            vibrato = 1.0 + 0.008 * math.sin(2 * math.pi * profile["vibrato"] * t)
            phase = 2 * math.pi * fundamental * t * vibrato
            # Harmonic source shaped by broad vowel formants.
            source = 0.0
            for h in range(1, 22):
                hz = fundamental * h
                def resonance(center):
                    width = max(100.0, center * 0.18)
                    return math.exp(-0.5 * ((hz-center)/width)**2)
                shape = (0.55*resonance(f1) + 0.8*resonance(f2) + 0.45*resonance(f3) + 0.035)
                source += math.sin(phase*h) * shape / (h ** 0.72)
            noise = (rng.random() * 2 - 1) * profile["breath"]
            audio[i] += amp * env * (source * 1.7 + noise)
    return {"syllables": len(units), "voice": voice}
