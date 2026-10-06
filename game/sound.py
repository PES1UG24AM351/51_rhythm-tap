import array
import math

import pygame

# Pitch per grade: better hit = higher pitch
GRADE_FREQS = {"PERFECT": 880, "GREAT": 660, "OK": 440}


def make_beep(freq, duration=0.08, volume=0.4):
    """Generate a short decaying sine beep as a pygame Sound (no asset files needed)."""
    init = pygame.mixer.get_init()
    if not init:
        return None
    rate, fmt, channels = init
    if fmt != -16:  # we generate signed 16-bit samples
        return None
    n = int(rate * duration)
    samples = array.array("h")
    for i in range(n):
        envelope = 1 - i / n  # linear fade-out avoids clicks
        value = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * i / rate))
        for _ in range(channels):
            samples.append(value)
    return pygame.mixer.Sound(buffer=samples.tobytes())


def load_hit_sounds():
    """Return {grade: Sound}. Empty dict if audio is unavailable (game still runs silently)."""
    try:
        pygame.mixer.init(44100, -16, 1, 512, allowedchanges=0)
    except pygame.error:
        return {}
    sounds = {}
    for grade, freq in GRADE_FREQS.items():
        snd = make_beep(freq)
        if snd:
            sounds[grade] = snd
    return sounds