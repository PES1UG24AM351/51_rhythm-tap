import pygame

LANES = 4
LANE_KEYS = [pygame.K_d, pygame.K_f, pygame.K_j, pygame.K_k]
LANE_LABELS = ['D', 'F', 'J', 'K']
LANE_COLORS = [(220,80,80),(80,180,220),(100,220,100),(220,180,60)]

class Note:
    WIDTH = 70
    HEIGHT = 20
    def __init__(self, lane, y=-30, speed=4):
        self.lane = lane
        self.y = y
        self.speed = speed
        self.hit = False
        self.missed = False

    def update(self):
        self.y += self.speed

    def get_rect(self, lane_x):
        return pygame.Rect(lane_x - self.WIDTH//2, int(self.y), self.WIDTH, self.HEIGHT)

    def is_offscreen(self, screen_h):
        return self.y > screen_h + 10


class HoldNote(Note):
    """A long note: press when the head reaches the hit line, then keep the key
    held while the body scrolls through (hold_frames frames = 1 second at 60 FPS).
    self.y is the HEAD (bottom edge); the body extends upward from it."""
    BODY_WIDTH = 30

    def __init__(self, lane, y=-30, speed=4, hold_frames=60):
        super().__init__(lane, y, speed)
        self.hold_frames = hold_frames
        self.length = speed * hold_frames   # body length in px = 1 second of scrolling
        self.holding = False
        self.held_frames = 0
        self.points = 0                     # base points from head accuracy, paid on completion

    def update(self):
        if self.holding:
            self.held_frames += 1           # head stays pinned on the hit line
        else:
            super().update()

    @property
    def completed(self):
        return self.holding and self.held_frames >= self.hold_frames

    def is_offscreen(self, screen_h):
        return self.y - self.length > screen_h + 10   # wait until the whole body is gone

    def get_body_rect(self, lane_x):
        remaining = int(max(0, self.length - self.held_frames * self.speed))
        bottom = int(self.y) + self.HEIGHT // 2
        return pygame.Rect(lane_x - self.BODY_WIDTH//2, bottom - remaining,
                           self.BODY_WIDTH, remaining)