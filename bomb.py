"""하늘에서 떨어지는 폭탄 (스테이지 2 전용).

- 폭탄은 sprites/object/bomb.png 로 그리며, 일정한 속도로 떨어져 지면에 닿는다.
- 지면에 닿기 3초 전부터 닿을 지점에 빨간 타원으로 피격 지점을 표시한다.
- 닿기 1.5초 전부터는 타원이 깜빡인다.
- 닿는 순간 그 타원 안에 있던 주인공은 피해를 입는다.
"""

import os
import random

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOMB_FILE = os.path.join(BASE_DIR, "sprites", "object", "bomb.png")
BOMB_SCALE = 0.12  # 원본 1024x1536 을 화면 크기로 줄이는 배율

EFFECT_FILE = os.path.join(BASE_DIR, "sprites", "object", "bomb_effect.png")
EFFECT_COLS = 5  # 효과 그림은 가로 5칸 x 세로 2칸 = 10프레임 시트다
EFFECT_ROWS = 2
EFFECT_FRAMES = EFFECT_COLS * EFFECT_ROWS
EFFECT_FRAME_TIME = 0.07  # 한 칸을 보여 주는 시간(초)
# 1부터 셀 때 5~7번째 프레임(불꽃이 가장 큰 부분)은 조금 더 오래 보여 준다.
EFFECT_HOLD_FRAMES = (4, 5, 6)  # 0부터 센 인덱스
EFFECT_HOLD_TIME = 0.11
EFFECT_WIDTH = 450  # 화면에 그리는 폭발 그림의 가로(px). 이전 300px 의 1.5배
# 효과 그림의 아래쪽 약 20px 은 비어 있어서, 불꽃 아랫부분이 발끝에 오도록 내린다.
EFFECT_BOTTOM_PAD = 20
# 프레임마다 보여 주는 시간과 애니메이션 전체 길이
EFFECT_DURATIONS = tuple(
    EFFECT_HOLD_TIME if i in EFFECT_HOLD_FRAMES else EFFECT_FRAME_TIME
    for i in range(EFFECT_FRAMES)
)
EFFECT_DURATION = sum(EFFECT_DURATIONS)

FALL_TIME = 1.0  # 하늘에서 지면까지 떨어지는 시간(초). 이전 5초의 5배 속도.
WARN_TIME = 3.0  # 닿기 몇 초 전부터 타원을 보여 줄지(생성 후 닿을 때까지의 시간)
LANDING_TIME = WARN_TIME  # 생성 후 지면에 닿기까지의 시간
DROP_START = LANDING_TIME - FALL_TIME  # 이 시간에 떨어지기 시작한다(그 전에는 하늘에 있다가 보이지 않는다)
BLINK_TIME = 1.5  # 닿기 몇 초 전부터 타원을 깜빡일지
BLINK_PERIOD = 0.2  # 깜빡임 한 번의 길이(켜짐/꺼짐 각각)

ELLIPSE_W = 340  # 피격 타원의 가로(px). 위험 표시와 폭발 범위가 같다.
ELLIPSE_H = 92  # 피격 타원의 세로(px)
ELLIPSE_COLOR = (235, 40, 40)

SPAWN_INTERVAL = 10.0  # 폭탄이 떨어지는 간격(초)
SCREEN_W = 1280  # 화면 가로(px). 폭탄은 플레이어 화면 안에 떨어진다.

_image = None
_effect_tex = None


def _bomb_image():
    global _image
    if _image is None:
        _image = pico2d.load_image(BOMB_FILE)
    return _image


def _effect_image():
    global _effect_tex
    if _effect_tex is None:
        _effect_tex = pico2d.load_image(EFFECT_FILE)
    return _effect_tex


class Bomb:
    def __init__(self, x, ground_y, sky_y):
        self.x = x
        self.ground_y = ground_y
        self.sky_y = sky_y
        self.t = 0.0
        self.exploded = False

    @property
    def landed(self):
        return self.t >= LANDING_TIME

    def y(self):
        progress = min(1.0, max(0.0, (self.t - DROP_START) / FALL_TIME))
        return self.sky_y + (self.ground_y - self.sky_y) * progress

    def dropping(self):
        """폭탄이 보이며 떨어지는 중인지."""
        return self.t >= DROP_START

    def warning_visible(self):
        """타원을 보여 줄 때인지(닿기 3초 전부터 닿을 때까지)."""
        remaining = LANDING_TIME - self.t
        return 0.0 < remaining <= WARN_TIME and not self.exploded

    def warning_alpha(self):
        """타원의 불투명도(0~255). 닿기 1.5초 전부터는 깜빡인다."""
        remaining = LANDING_TIME - self.t
        if remaining > BLINK_TIME:
            return 150
        on = int(self.t / BLINK_PERIOD) % 2 == 0
        return 230 if on else 40

    def hit_rect(self):
        """피격 판정 사각형 (left, bottom, width, height)."""
        return (self.x - ELLIPSE_W * 0.5, self.ground_y - ELLIPSE_H * 0.5,
                ELLIPSE_W, ELLIPSE_H)

    def update(self, dt):
        self.t += dt

    def draw_warning(self, art, camera_x, shake_x=0.0):
        if not self.warning_visible():
            return
        disc = art.disc(ELLIPSE_COLOR)
        cx = self.x - camera_x + shake_x
        art.blit(disc, cx, self.ground_y, ELLIPSE_W, ELLIPSE_H, self.warning_alpha())

    def draw(self, camera_x, shake_x=0.0):
        if self.exploded or not self.dropping():
            return
        image = _bomb_image()
        w = image.w * BOMB_SCALE
        h = image.h * BOMB_SCALE
        cx = self.x - camera_x + shake_x
        # 그림의 아래쪽 끝(뾰족한 부분)이 폭탄의 y 에 오도록 한다.
        cy = self.y() + h * 0.5
        image.clip_composite_draw(0, 0, image.w, image.h, 0.0, "",
                                  cx, cy, w, h)


class Blast:
    """폭탄이 터질 때 자리에 남는 폭발 효과 애니메이션."""

    def __init__(self, x, ground_y):
        self.x = x
        self.ground_y = ground_y
        self.t = 0.0

    @property
    def finished(self):
        return self.t >= EFFECT_DURATION

    def update(self, dt):
        self.t += dt

    def frame_index(self):
        """지금 보여 줄 프레임 번호. 프레임마다 보여 주는 시간이 다르다."""
        left = self.t
        for index, duration in enumerate(EFFECT_DURATIONS):
            if left < duration:
                return index
            left -= duration
        return EFFECT_FRAMES - 1

    def draw(self, camera_x, shake_x=0.0):
        if self.finished:
            return
        image = _effect_image()
        cell_w = image.w / EFFECT_COLS
        cell_h = image.h / EFFECT_ROWS
        frame = self.frame_index()
        col = frame % EFFECT_COLS
        row = frame // EFFECT_COLS
        # pico2d 의 bottom 은 이미지의 아래쪽에서 잰 거리라, 첫 줄(그림의 위쪽 칸)이
        # 애니메이션 앞부분이 되도록 뒤집어 준다.
        sx = round(col * cell_w)
        sw = round((col + 1) * cell_w) - sx
        sb = round((EFFECT_ROWS - 1 - row) * cell_h)
        sh = round((EFFECT_ROWS - row) * cell_h) - sb
        scale = EFFECT_WIDTH / cell_w
        w = sw * scale
        h = sh * scale
        cx = self.x - camera_x + shake_x
        # 그림의 아래쪽 끝(불꽃 아랫부분)이 발끝 높이에 오도록 한다.
        cy = self.ground_y + h * 0.5 - EFFECT_BOTTOM_PAD * scale
        image.clip_composite_draw(sx, sb, sw, sh, 0.0, "",
                                  cx, cy, w, h)


class BombField:
    """스테이지 안의 폭탄 생성과 갱신을 맡는다."""

    def __init__(self, ground_spans, sky_y, ground_y, enabled):
        self.ground_spans = list(ground_spans)
        self.sky_y = sky_y
        self.ground_y = ground_y
        self.enabled = enabled
        self.bombs = []
        self.blasts = []
        self.timer = SPAWN_INTERVAL

    def _random_x(self, camera_x):
        """화면 안의 땅 위에서 무작위 x. 화면 안에 땅이 없으면 None."""
        view_left = camera_x + ELLIPSE_W * 0.5
        view_right = camera_x + SCREEN_W - ELLIPSE_W * 0.5
        candidates = []
        for left, right in self.ground_spans:
            lo = max(left + ELLIPSE_W * 0.5, view_left)
            hi = min(right - ELLIPSE_W * 0.5, view_right)
            if lo < hi:
                candidates.append((lo, hi))
        if not candidates:
            return None
        lo, hi = random.choice(candidates)
        return random.uniform(lo, hi)

    def update(self, dt, camera_x=0.0):
        """폭탄을 움직이고, 닿은 폭탄을 돌려준다(주인공 피격 판정은 호출한 쪽이 한다)."""
        landed = []
        if self.enabled:
            self.timer -= dt
            if self.timer <= 0.0:
                self.timer += SPAWN_INTERVAL
                x = self._random_x(camera_x)
                if x is not None:
                    self.bombs.append(Bomb(x, self.ground_y, self.sky_y))
        for bomb in self.bombs:
            was_landed = bomb.landed
            bomb.update(dt)
            if bomb.landed and not was_landed:
                bomb.exploded = True
                landed.append(bomb)
                self.blasts.append(Blast(bomb.x, bomb.ground_y))
        self.bombs = [b for b in self.bombs if not b.exploded]
        for blast in self.blasts:
            blast.update(dt)
        self.blasts = [b for b in self.blasts if not b.finished]
        return landed

    def draw_warnings(self, art, camera_x, shake_x=0.0):
        for bomb in self.bombs:
            bomb.draw_warning(art, camera_x, shake_x)

    def draw(self, camera_x, shake_x=0.0):
        for bomb in self.bombs:
            bomb.draw(camera_x, shake_x)

    def draw_blasts(self, camera_x, shake_x=0.0):
        for blast in self.blasts:
            blast.draw(camera_x, shake_x)
