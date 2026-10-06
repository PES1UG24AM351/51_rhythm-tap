import pygame
import random
from game.beat import Note, HoldNote, LANES, LANE_KEYS, LANE_LABELS, LANE_COLORS
from game.sound import load_hit_sounds

WIDTH, HEIGHT = 480, 640
FPS = 60
BPM = 120                   # notes spawn exactly on these beats
HIT_Y = HEIGHT - 80
HIT_WINDOW = 30
BG = (15, 10, 25)
LANE_W = WIDTH // LANES
HOLD_FRAMES = FPS * 1       # hold notes must be held for 1 second
HOLD_CHANCE = 0.25          # fraction of spawns that are hold notes
HOLD_GAP_FRAMES = 20        # breathing room in a lane after a hold note
HOLD_BONUS = 2              # hold notes are worth 2x a tap of the same grade

class GameEngine:
    def __init__(self):
        pygame.init()
        self.hit_sounds,self.hold_sounds = load_hit_sounds()  # {} if no audio device
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rhythm Tap")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 26, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.reset()

    def _stop_hold_sound(self, note):
        ch = getattr(note, 'sound_channel', None)
        if ch:
            ch.fadeout(30)
            note.sound_channel = None

    def reset(self):
        if pygame.mixer.get_init():
            pygame.mixer.stop()
        self.notes = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.misses = 0
        self.bpm = BPM
        self.beat_interval = FPS * 60.0 / self.bpm   # frames per beat (30 at 120 BPM)
        self.beat_counter = 0.0
        self.lane_free_frame = [0] * LANES   # lane is blocked by a hold note until this frame
        self.speed = 5
        self.frame = 0
        self.feedback = []  # (text, color, ttl, x, y)
        self.game_over = False
        self.counts = {"PERFECT": 0, "GREAT": 0, "OK": 0}

    def spawn_note(self):
        free = [l for l in range(LANES) if self.frame >= self.lane_free_frame[l]]
        if not free:
            return
        lane = random.choice(free)
        if random.random() < HOLD_CHANCE:
            self.notes.append(HoldNote(lane, y=-30, speed=self.speed, hold_frames=HOLD_FRAMES))
            # the body takes HOLD_FRAMES frames to scroll in; keep the lane clear until then
            self.lane_free_frame[lane] = self.frame + HOLD_FRAMES + HOLD_GAP_FRAMES
        else:
            self.notes.append(Note(lane, y=-30, speed=self.speed))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif not self.game_over:
                    for i, key in enumerate(LANE_KEYS):
                        if event.key == key:
                            self.process_tap(i)
            if event.type == pygame.KEYUP and not self.game_over:
                for i, key in enumerate(LANE_KEYS):
                    if event.key == key:
                        self.process_release(i)
        return True

    def process_release(self, lane):
        # Releasing a key before the hold is complete drops the note
        lane_x = lane * LANE_W + LANE_W // 2
        for note in self.notes:
            if isinstance(note, HoldNote) and note.lane == lane and note.holding and not note.hit:
                note.hit = True          # consume it so it disappears
                self._stop_hold_sound(note)
                self.combo = 0
                self.misses += 1
                self.feedback.append(["DROP", (220,60,60), 40, lane_x, HIT_Y - 30])

    def process_tap(self, lane):
        # Find closest note in this lane near hit zone
        best = None
        best_dist = 9999
        for note in self.notes:
            if note.lane == lane and not note.hit and not note.missed and not getattr(note, 'holding', False):
                dist = abs(note.y + Note.HEIGHT//2 - HIT_Y)
                if dist < best_dist:
                    best_dist = dist
                    best = note
        lane_x = lane * LANE_W + LANE_W // 2
        if best and best_dist <= HIT_WINDOW:
            if best_dist < 8:
                grade, pts = "PERFECT", 300
                col = (255, 220, 0)
            elif best_dist < 18:
                grade, pts = "GREAT", 200
                col = (100, 220, 100)
            else:
                grade, pts = "OK", 100
                col = (180, 180, 255)
            self.feedback.append([grade, col, 40, lane_x, HIT_Y - 30])
            snd = self.hit_sounds.get(grade)
            if snd:
                snd.play()
            if isinstance(best, HoldNote):
                # Head judged now, but points are only paid after a full 1s hold
                best.holding = True
                best.points = pts
                best.grade = grade
                best.y = HIT_Y - Note.HEIGHT // 2
                hold_snd = self.hold_sounds.get(grade)
                if hold_snd:
                    best.sound_channel = hold_snd.play(loops=-1)     # snap head onto the hit line
            else:
                best.hit = True
                self.counts[grade] += 1
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self.score += pts * max(1, self.combo // 5)
        else:
            self.combo = 0
            self.misses += 1
            self.feedback.append(["MISS", (220,60,60), 40, lane_x, HIT_Y - 30])

    def update(self):
        if self.game_over: return
        self.frame += 1
        # Difficulty ramp: faster scroll only. Spawn rate is locked to the BPM.
        if self.frame % 600 == 0:
            self.speed = min(10, self.speed + 0.5)

        # Beat clock: subtracting the interval, instead of zeroing, keeps it drift-free
        self.beat_counter += 1
        if self.beat_counter >= self.beat_interval:
            self.beat_counter -= self.beat_interval
            self.spawn_note()

        for note in self.notes:
            note.update()
            if not note.hit and not note.missed and note.y > HIT_Y + HIT_WINDOW + Note.HEIGHT:
                note.missed = True
                self.misses += 1
                self.combo = 0
            if isinstance(note, HoldNote) and note.completed and not note.hit:
                note.hit = True
                self.counts[note.grade] += 1
                self._stop_hold_sound(note)
                self.combo += 1
                self.max_combo = max(self.max_combo, self.combo)
                self.score += note.points * HOLD_BONUS * max(1, self.combo // 5)
                lane_x = note.lane * LANE_W + LANE_W // 2
                self.feedback.append(["HOLD!", (255, 220, 0), 40, lane_x, HIT_Y - 30])

        self.notes = [n for n in self.notes if not (n.hit or n.missed and n.is_offscreen(HEIGHT))]
        self.feedback = [[t,c,ttl-1,x,y] for t,c,ttl,x,y in self.feedback if ttl > 1]

        if self.misses >= 15:
            self.game_over = True
            if pygame.mixer.get_init():
                pygame.mixer.stop()

    def accuracy(self):
        """Weighted: PERFECT=100%, GREAT=2/3, OK=1/3, MISS=0, averaged over all judged notes."""
        total = sum(self.counts.values()) + self.misses
        if total == 0:
            return 0.0
        earned = (self.counts["PERFECT"] * 300 + self.counts["GREAT"] * 200
                  + self.counts["OK"] * 100)
        return 100.0 * earned / (total * 300)

    def draw(self):
        self.screen.fill(BG)
        # Lane dividers
        for i in range(LANES + 1):
            pygame.draw.line(self.screen, (40,40,60), (i*LANE_W,0), (i*LANE_W,HEIGHT), 1)

        # Hit line
        pygame.draw.line(self.screen, (80,80,100), (0,HIT_Y), (WIDTH,HIT_Y), 2)
        for i in range(LANES):
            lx = i*LANE_W + LANE_W//2
            pygame.draw.rect(self.screen, LANE_COLORS[i],
                pygame.Rect(lx - Note.WIDTH//2, HIT_Y - 12, Note.WIDTH, 24), border_radius=6)
            lbl = self.font.render(LANE_LABELS[i], True, (20,20,20))
            self.screen.blit(lbl, (lx - lbl.get_width()//2, HIT_Y - 10))

        # Notes
        for note in self.notes:
            if note.hit: continue
            lx = note.lane * LANE_W + LANE_W // 2
            color = LANE_COLORS[note.lane]
            if isinstance(note, HoldNote):
                if note.missed:
                    color, body_col = (90, 90, 90), (50, 50, 50)
                elif note.holding:
                    body_col = color
                else:
                    body_col = tuple(c // 2 for c in color)
                pygame.draw.rect(self.screen, body_col, note.get_body_rect(lx), border_radius=8)
            rect = note.get_rect(lx)
            pygame.draw.rect(self.screen, color, rect, border_radius=5)
            if isinstance(note, HoldNote) and note.holding:
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 3, border_radius=5)

        # Feedback
        for text, color, ttl, x, y in self.feedback:
            surf = self.font.render(text, True, color)
            alpha = min(255, ttl * 7)
            surf.set_alpha(alpha)
            self.screen.blit(surf, (x - surf.get_width()//2, y))

        # HUD
        sc = self.font.render(f"Score: {self.score}", True, (220,220,220))
        co = self.font.render(f"Combo: {self.combo}x", True, (255,220,80))
        mi = self.font.render(f"Misses: {self.misses}/15", True, (220,100,100))
        self.screen.blit(sc, (10, 10))
        self.screen.blit(co, (10, 40))
        self.screen.blit(mi, (WIDTH - 170, 10))

        if self.game_over:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 190))
            self.screen.blit(ov, (0, 0))

            def center(surf, y):
                self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))

            center(self.big_font.render("GAME OVER", True, (220, 60, 60)), 110)
            center(self.font.render(f"Score: {self.score}", True, (220, 220, 220)), 175)
            center(self.font.render(f"Max Combo: {self.max_combo}x", True, (255, 220, 80)), 210)

            rows = [
                ("PERFECT", self.counts["PERFECT"], (255, 220, 0)),
                ("GREAT",   self.counts["GREAT"],   (100, 220, 100)),
                ("OK",      self.counts["OK"],      (180, 180, 255)),
                ("MISS",    self.misses,            (220, 60, 60)),
            ]
            y = 275
            for label, value, col in rows:
                self.screen.blit(self.font.render(label, True, col), (110, y))
                num = self.font.render(str(value), True, col)
                self.screen.blit(num, (WIDTH - 110 - num.get_width(), y))
                y += 36

            pygame.draw.line(self.screen, (90, 90, 110), (100, y + 4), (WIDTH - 100, y + 4), 2)
            center(self.font.render(f"Accuracy: {self.accuracy():.1f}%", True, (255, 255, 255)), y + 16)
            center(self.font.render("Press R to Restart", True, (160, 160, 160)), y + 70)
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()