import array
import math

import pygame

GRADE_FREQS = {"PERFECT": 880, "GREAT": 660, "OK": 440}


def _tone(freq, duration, volume, decay=True, loopable=False):
    init = pygame.mixer.get_init()
    if not init:
        return None
    rate, fmt, channels = init
    if fmt != -16:
        return None

    if loopable:
        # whole number of cycles, so the loop point has no click
        cycles = max(1, round(freq * duration))
        n = int(round(cycles * rate / freq))
        omega = 2 * math.pi * cycles / n
    else:
        n = int(rate * duration)
        omega = 2 * math.pi * freq / rate

    samples = array.array("h")
    for i in range(n):
        env = (1 - i / n) if decay else 1.0
        v = int(32767 * volume * env * math.sin(omega * i))
        for _ in range(channels):
            samples.append(v)
    return pygame.mixer.Sound(buffer=samples.tobytes())


def load_hit_sounds():
    """Return (hit_sounds, hold_sounds), each {grade: Sound}. Empty dicts if no audio."""
    try:
        pygame.mixer.init(44100, -16, 1, 512, allowedchanges=0)
    except pygame.error:
        return {}, {}
    hits, holds = {}, {}
    for grade, freq in GRADE_FREQS.items():
        s = _tone(freq, 0.08, 0.4)
        if s:
            hits[grade] = s
        h = _tone(freq, 0.1, 0.2, decay=False, loopable=True)
        if h:
            holds[grade] = h
    return hits, holds