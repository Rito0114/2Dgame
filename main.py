"""그림자 소녀 (Shadow Girl)

pico2d 로 만든 횡스크롤 액션 플랫포머.

    python main.py

조작
    A / D  또는  ← / → : 이동
    SPACE / W / ↑       : 점프
    J / X               : 공격
    P                    : 일시정지
    R                    : 재시작
    ESC                  : 종료

캐릭터 클래스는 girl.py 에 분리되어 있다.
"""

import ctypes
import math
import os
import random
import sys

import pico2d
import sdl2

from girl import Girl

WIDTH, HEIGHT = 1280, 720
GROUND = 140
WORLD_W = 7000
FPS = 60

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(
    os.path.dirname(pico2d.__file__), "data", "ConsolaMalgun.ttf"
)


# ---------------------------------------------------------------------------
# 작은 도우미들
# ---------------------------------------------------------------------------
def overlaps(ax, ay, aw, ah, bx, by, bw, bh):
    """AABB 충돌 (y 는 위쪽이 +)."""
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def clamp(value, low, high):
    return max(low, min(high, value))


def enable_alpha_blending():
    """도형에도 알파 블렌딩이 적용되게 한다."""
    try:
        pico2d.SDL_SetRenderDrawBlendMode(
            pico2d.pico2d.renderer, pico2d.SDL_BLENDMODE_BLEND
        )
    except Exception:
        pass


def patch_draw_primitives():
    """pico2d 의 도형 함수는 정수 인자만 받는다.

    애니메이션 계산을 하다 보면 좌표/반지름/알파가 실수가 되기 쉬운데
    그대로 넘기면 TypeError 가 나므로, 실수를 안전하게 정수로 변환해서
    넘기도록 감싼다. (girl.py 도 같은 pico2d 모듈을 쓰므로 함께 적용된다.)
    """
    base_circle = pico2d.draw_circle
    base_rectangle = pico2d.draw_rectangle
    base_line = pico2d.draw_line

    def draw_circle(x, y, radius, r=0, g=0, b=0, a=255, filled=False):
        base_circle(x, y, max(1, int(radius)),
                    int(r), int(g), int(b), int(a), filled=filled)

    def draw_rectangle(x1, y1, x2, y2, r=255, g=0, b=0, a=255, filled=False):
        base_rectangle(x1, y1, x2, y2,
                       int(r), int(g), int(b), int(a), filled=filled)

    def draw_line(x1, y1, x2, y2, r=0, g=0, b=0, a=255):
        base_line(x1, y1, x2, y2, int(r), int(g), int(b), int(a))

    pico2d.draw_circle = draw_circle
    pico2d.draw_rectangle = draw_rectangle
    pico2d.draw_line = draw_line


class TextRenderer:
    """폰트 캐시 + 가운데 정렬을 지원하는 텍스트 도우미."""

    def __init__(self):
        self._fonts = {}
        self._widths = {}

    def font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pico2d.load_font(FONT_PATH, size)
        return self._fonts[size]

    def measure(self, size, text):
        key = (size, text)
        if key not in self._widths:
            w = ctypes.c_int(0)
            h = ctypes.c_int(0)
            pico2d.TTF_SizeUTF8(
                self.font(size).font,
                text.encode("utf-8"),
                ctypes.byref(w),
                ctypes.byref(h),
            )
            self._widths[key] = w.value
        return self._widths[key]

    def draw(self, size, x, y, text, color=(238, 238, 250),
             align="left", shadow=(8, 8, 20)):
        if align == "center":
            x -= self.measure(size, text) * 0.5
        elif align == "right":
            x -= self.measure(size, text)
        if shadow is not None:
            self.font(size).draw(x + 2, y - 2, text, shadow)
        self.font(size).draw(x, y, text, color)


class Platform:
    __slots__ = ("left", "bottom", "width", "height", "one_way")

    def __init__(self, left, bottom, width, height, one_way=False):
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height
        # one_way(단방향) 발판은 아래에서 점프해 통과하고, 위에서만 착지한다.
        self.one_way = one_way

    @property
    def right(self):
        return self.left + self.width

    @property
    def top(self):
        return self.bottom + self.height


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "radius", "color", "gravity")

    def __init__(self, x, y, vx, vy, life, radius, color, gravity=900.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color
        self.gravity = gravity

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy -= self.gravity * dt
        self.vx *= 0.99
        self.life -= dt

    def draw(self, camera_x, shake_x=0.0):
        if self.life <= 0:
            return
        alpha = int(255 * max(0.0, self.life / self.max_life))
        radius = max(1, int(self.radius * (0.4 + 0.6 * self.life / self.max_life)))
        pico2d.draw_circle(
            self.x - camera_x + shake_x,
            self.y,
            radius,
            self.color[0], self.color[1], self.color[2], alpha,
            filled=True,
        )


class Slash:
    """공격 이펙트(초승달 모양)."""

    def __init__(self, x, y, facing):
        self.x = x
        self.y = y
        self.facing = facing
        self.life = 0.18
        self.max_life = 0.18

    def update(self, dt):
        self.life -= dt

    def draw(self, camera_x, shake_x=0.0):
        if self.life <= 0:
            return
        ratio = self.life / self.max_life
        alpha = int(230 * ratio)
        cx = self.x - camera_x + shake_x + self.facing * 40
        cy = self.y + 100
        for band, radius in enumerate((56, 68, 80)):
            color = (220, 245, 255) if band == 1 else (140, 220, 235)
            for i in range(7):
                a1 = math.radians(-64 + i * 18)
                a2 = math.radians(-64 + (i + 1) * 18)
                x1 = cx + math.cos(a1) * radius * self.facing
                y1 = cy + math.sin(a1) * radius
                x2 = cx + math.cos(a2) * radius * self.facing
                y2 = cy + math.sin(a2) * radius
                pico2d.draw_line(
                    x1, y1, x2, y2,
                    color[0], color[1], color[2], alpha,
                )


class Coin:
    __slots__ = ("x", "y", "phase", "taken")

    def __init__(self, x, y, phase):
        self.x = x
        self.y = y
        self.phase = phase
        self.taken = False


class HeartPickup:
    __slots__ = ("x", "y", "phase", "taken")

    def __init__(self, x, y, phase):
        self.x = x
        self.y = y
        self.phase = phase
        self.taken = False


class Checkpoint:
    __slots__ = ("x", "y", "active")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = False


class Enemy:
    WIDTH = {"slime": 58, "wisp": 48}
    HEIGHT = {"slime": 46, "wisp": 46}

    def __init__(self, kind, x, y, left, right, phase=0.0):
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.ax = float(x)
        self.ay = float(y)
        self.left = left
        self.right = right
        self.width = self.WIDTH[kind]
        self.height = self.HEIGHT[kind]
        self.phase = phase
        self.vx = -78.0
        self.alive = True
        self.last_attack = -1

    @property
    def top(self):
        return self.y + self.height

    def rect(self):
        return (
            self.x - self.width * 0.5,
            self.y,
            self.width,
            self.height,
        )

    def update(self, dt, time):
        if not self.alive:
            return
        if self.kind == "slime":
            self.x += self.vx * dt
            half = self.width * 0.5
            if self.x < self.left + half:
                self.x = self.left + half
                self.vx = abs(self.vx)
            elif self.x > self.right - half:
                self.x = self.right - half
                self.vx = -abs(self.vx)
        else:
            self.x = self.ax + math.sin(time * 1.1 + self.phase) * 42.0
            self.y = self.ay + math.sin(time * 2.4 + self.phase) * 16.0

    def draw(self, camera_x, time, shake_x=0.0):
        if not self.alive:
            return
        x = self.x - camera_x + shake_x
        if x < -80 or x > WIDTH + 80:
            return
        if self.kind == "slime":
            self._draw_slime(x, time)
        else:
            self._draw_wisp(x, time)

    def _draw_slime(self, x, time):
        squash = 1.0 + math.sin(time * 6.0 + self.phase) * 0.06
        y = self.y
        # 그림자
        pico2d.draw_circle(x, y + 5, 25, 8, 8, 20, 90, filled=True)
        # 몸통(원 3개를 겹쳐서 슬라임 모양)
        pico2d.draw_circle(x - 13, y + 17, 20, 28, 18, 48, 255, filled=True)
        pico2d.draw_circle(x + 13, y + 17, 20, 28, 18, 48, 255, filled=True)
        pico2d.draw_circle(x, y + 24 * squash, 22, 38, 24, 66, 255, filled=True)
        # 하이라이트
        pico2d.draw_circle(x - 8, y + 34, 7, 92, 62, 140, 220, filled=True)
        # 눈
        eye = 4 if self.vx >= 0 else -4
        pico2d.draw_circle(x - 8 + eye, y + 26, 5, 170, 255, 230, 255, filled=True)
        pico2d.draw_circle(x + 8 + eye, y + 26, 5, 170, 255, 230, 255, filled=True)
        pico2d.draw_circle(x - 8 + eye, y + 26, 2, 20, 20, 30, 255, filled=True)
        pico2d.draw_circle(x + 8 + eye, y + 26, 2, 20, 20, 30, 255, filled=True)

    def _draw_wisp(self, x, time):
        y = self.y + self.height * 0.5
        glow = int(26 + 12 * math.sin(time * 3.0 + self.phase))
        pico2d.draw_circle(x, y, 30, 150, 100, 255, glow, filled=True)
        pico2d.draw_circle(x, y, 20, 120, 70, 220, 60, filled=True)
        pico2d.draw_circle(x, y, 12, 200, 160, 255, 255, filled=True)
        # 꼬리
        for i, off in enumerate((14, 24, 34)):
            pico2d.draw_circle(
                x + math.sin(time * 4 + i) * 4,
                y - off,
                7 - i,
                130, 90, 220, 90 - i * 25,
                filled=True,
            )
        # 눈
        pico2d.draw_circle(x - 4, y + 3, 2, 255, 255, 255, 255, filled=True)
        pico2d.draw_circle(x + 4, y + 3, 2, 255, 255, 255, 255, filled=True)


class World:
    def __init__(self):
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.hearts = []
        self.checkpoints = []
        self.goal_x = 6720
        self.goal_y = GROUND
        self.stars = []
        rng = random.Random(11)
        for _ in range(80):
            self.stars.append(
                (
                    rng.uniform(0, WIDTH + 200),
                    rng.uniform(260, 700),
                    rng.choice((1, 1, 1, 2, 2, 3)),
                    rng.uniform(0.0, math.tau),
                )
            )
        self._build()

    # ------------------------------------------------------------------
    def _add_ground(self, left, right):
        self.platforms.append(
            Platform(left, GROUND - 240, right - left, 240)
        )

    def _add_platform(self, left, top, width, height=24):
        # 떠 있는 발판은 단방향: 아래에서 점프해 올라가고, 위에서만 딛는다.
        self.platforms.append(
            Platform(left, top - height, width, height, one_way=True)
        )

    def _add_coin(self, x, y):
        self.coins.append(Coin(x, y, random.random() * math.tau))

    def _coin_arc(self, cx, base_y, count=5, spacing=42, lift=70):
        for i in range(count):
            offset = i - (count - 1) * 0.5
            y = base_y + lift - abs(offset) * 14.0
            self._add_coin(cx + offset * spacing, y)

    def _coin_line(self, x1, x2, y, step=50):
        x = x1
        while x <= x2:
            self._add_coin(x, y)
            x += step

    def _add_slime(self, x, ground_y, left, right):
        self.enemies.append(
            Enemy("slime", x, ground_y, left, right, random.random() * math.tau)
        )

    def _add_wisp(self, x, y):
        self.enemies.append(
            Enemy("wisp", x, y, x - 50, x + 50, random.random() * math.tau)
        )

    # ------------------------------------------------------------------
    def _build(self):
        # 땅(중간중간 구멍이 있다)
        segments = [
            (0, 1500),
            (1640, 2900),
            (3040, 4200),
            (4360, 5500),
            (5660, 6900),
        ]
        for left, right in segments:
            self._add_ground(left, right)

        # 떠 있는 발판 (left, top, width)
        platforms = [
            (420, 260, 180), (700, 380, 180), (980, 260, 160),
            (1740, 260, 200), (2050, 380, 180), (2350, 300, 200),
            (2650, 440, 160),
            (3140, 260, 160), (3420, 360, 200), (3720, 280, 160),
            (4000, 420, 180),
            (4500, 280, 180), (4800, 400, 180), (5100, 300, 200),
            (5350, 240, 160),
            (5800, 260, 180), (6100, 380, 200), (6400, 280, 160),
        ]
        for left, top, width in platforms:
            self._add_platform(left, top, width)

        # 체크포인트
        self.checkpoints = [Checkpoint(2000, GROUND), Checkpoint(4500, GROUND)]

        # 코인
        self._coin_line(180, 400, 200)
        self._coin_arc(300, 190, 5, 42, 80)
        self._coin_arc(520, 330, 5, 40, 60)
        self._coin_arc(790, 470, 5, 44, 60)
        self._coin_arc(1000, 330, 3, 44, 50)
        self._coin_arc(1160, 200, 3, 40, 40)
        self._coin_arc(1570, 250, 5, 40, 70)
        self._coin_arc(1760, 210, 4, 42, 50)
        self._coin_arc(2140, 460, 5, 40, 60)
        self._coin_arc(2380, 360, 3, 40, 50)
        self._coin_arc(2600, 210, 4, 42, 45)
        self._coin_arc(2970, 260, 5, 40, 70)
        self._coin_arc(3300, 320, 4, 40, 50)
        self._coin_arc(3500, 430, 3, 38, 45)
        self._coin_arc(3780, 350, 4, 42, 50)
        self._coin_arc(4060, 300, 4, 40, 50)
        self._coin_arc(4270, 250, 5, 40, 70)
        self._coin_line(4480, 4660, 200)
        self._coin_arc(4600, 330, 4, 40, 50)
        self._coin_arc(4920, 470, 3, 38, 40)
        self._coin_arc(5200, 370, 4, 40, 50)
        self._coin_arc(5570, 260, 5, 40, 70)
        self._coin_arc(5850, 320, 4, 42, 50)
        self._coin_arc(6200, 450, 3, 38, 45)
        self._coin_arc(6500, 340, 4, 42, 50)

        # 회복 아이템
        self.hearts = [
            HeartPickup(1200, GROUND + 40, 0.0),
            HeartPickup(3500, 410, 1.7),
            HeartPickup(6000, GROUND + 40, 3.2),
        ]

        # 슬라임
        self._add_slime(780, GROUND, 700, 1500)
        self._add_slime(1250, GROUND, 1150, 1490)
        self._add_slime(1750, GROUND, 1640, 1900)
        self._add_slime(2450, GROUND, 2300, 2650)
        self._add_slime(2810, GROUND, 2700, 2890)
        self._add_slime(3250, GROUND, 3040, 3400)
        self._add_slime(3600, GROUND, 3450, 3700)
        self._add_slime(3960, GROUND, 3800, 4180)
        self._add_slime(4550, GROUND, 4360, 4700)
        self._add_slime(5050, GROUND, 4900, 5200)
        self._add_slime(5450, GROUND, 5300, 5490)
        self._add_slime(5900, GROUND, 5660, 6000)
        self._add_slime(6300, GROUND, 6120, 6500)
        self._add_slime(6600, GROUND, 6500, 6880)
        # 발판 위 슬라임
        self._add_slime(2140, 380, 2050, 2230)
        self._add_slime(3520, 360, 3420, 3620)
        self._add_slime(4890, 400, 4800, 4980)
        self._add_slime(6200, 380, 6100, 6300)

        # 위습(날아다니는 적)
        self._add_wisp(1350, 300)
        self._add_wisp(2200, 430)
        self._add_wisp(3200, 330)
        self._add_wisp(4300, 350)
        self._add_wisp(5000, 430)
        self._add_wisp(5750, 320)
        self._add_wisp(6450, 400)

    # ------------------------------------------------------------------
    # 배경
    # ------------------------------------------------------------------
    def draw_background(self, camera_x, time, shake_x=0.0):
        # 하늘 그라데이션
        bands = 30
        for i in range(bands):
            f = i / (bands - 1)
            r = int(92 + (10 - 92) * f)
            g = int(56 + (12 - 56) * f)
            b = int(112 + (34 - 112) * f)
            y1 = i * (HEIGHT / bands)
            y2 = y1 + HEIGHT / bands + 1
            pico2d.draw_rectangle(0, y1, WIDTH, y2, r, g, b, filled=True)

        # 별
        for sx, sy, size, phase in self.stars:
            x = (sx - camera_x * 0.04) % (WIDTH + 200) - 100
            alpha = 90 + int(110 * abs(math.sin(time * 0.9 + phase)))
            pico2d.draw_rectangle(x, sy, x + size, sy + size, 220, 225, 255,
                                  alpha, filled=True)

        # 달
        mx = 1040 - camera_x * 0.05 + shake_x * 0.1
        my = 552
        pico2d.draw_circle(mx, my, 96, 255, 226, 180, 14, filled=True)
        pico2d.draw_circle(mx, my, 72, 255, 226, 180, 22, filled=True)
        pico2d.draw_circle(mx, my, 54, 244, 238, 212, 255, filled=True)
        pico2d.draw_circle(mx - 16, my + 12, 10, 210, 200, 180, 255, filled=True)
        pico2d.draw_circle(mx + 18, my - 14, 7, 210, 200, 180, 255, filled=True)
        pico2d.draw_circle(mx + 4, my + 28, 5, 214, 204, 184, 255, filled=True)

        # 멀리 있는 산맥
        offset = camera_x * 0.12
        for x in range(-32, WIDTH + 32, 16):
            wx = x + offset
            h = 95 + 55 * math.sin(wx * 0.006) + 28 * math.sin(wx * 0.017 + 1.7)
            h = max(35, h)
            pico2d.draw_rectangle(x, 80, x + 17, 80 + h, 38, 30, 76,
                                  filled=True)
        # 가까운 언덕
        offset = camera_x * 0.28
        for x in range(-32, WIDTH + 32, 16):
            wx = x + offset
            h = 62 + 34 * math.sin(wx * 0.009 + 2.2) + 18 * math.sin(wx * 0.023)
            h = max(25, h)
            pico2d.draw_rectangle(x, 60, x + 17, 60 + h, 24, 20, 54,
                                  filled=True)

        # 지평선 안개
        for i in range(6):
            alpha = 26 - i * 4
            pico2d.draw_rectangle(
                0, GROUND + i * 14, WIDTH, GROUND + (i + 1) * 14 + 1,
                160, 120, 200, alpha, filled=True,
            )

        # 땅 아래(구멍으로 보이는 어두운 골짜기)
        pico2d.draw_rectangle(0, 0, WIDTH, GROUND, 10, 10, 26, filled=True)

    # ------------------------------------------------------------------
    # 발판
    # ------------------------------------------------------------------
    def draw_platforms(self, camera_x, shake_x=0.0):
        for p in self.platforms:
            x = p.left - camera_x + shake_x
            if x + p.width < -40 or x > WIDTH + 40:
                continue
            top = p.top
            bottom = p.bottom
            # 본체
            pico2d.draw_rectangle(x, bottom, x + p.width, top - 12,
                                  18, 24, 46, filled=True)
            # 위쪽 잔디/네온 테두리
            pico2d.draw_rectangle(x, top - 12, x + p.width, top - 7,
                                  34, 116, 126, filled=True)
            pico2d.draw_rectangle(x, top - 7, x + p.width, top,
                                  62, 226, 196, filled=True)
            # 외곽선
            pico2d.draw_rectangle(x + 1, bottom + 1, x + p.width - 1, top - 1,
                                  44, 60, 100)
            # 두꺼운 땅의 결
            if p.height > 80:
                yy = bottom + 30
                while yy < top - 26:
                    pico2d.draw_line(x + 8, yy, x + p.width - 8, yy,
                                     26, 34, 60)
                    yy += 46
            # 잔디 포기
            spacing = 52
            wx = int(p.left // spacing) * spacing
            while wx < p.left + p.width:
                sx = wx - camera_x + shake_x
                if -8 < sx < WIDTH + 8:
                    lean = 3 if (wx // spacing) % 2 == 0 else -3
                    pico2d.draw_line(sx, top, sx + lean, top + 9,
                                     58, 222, 192)
                    pico2d.draw_line(sx + 5, top, sx + 8, top + 6,
                                     42, 168, 160)
                wx += spacing

    def draw_checkpoints(self, camera_x, time, shake_x=0.0):
        for cp in self.checkpoints:
            x = cp.x - camera_x + shake_x
            if x < -60 or x > WIDTH + 60:
                continue
            y = cp.y
            color = (90, 240, 210) if cp.active else (90, 100, 140)
            # 기둥
            pico2d.draw_rectangle(x - 4, y, x + 4, y + 104, 24, 30, 54,
                                  filled=True)
            pico2d.draw_rectangle(x - 8, y, x + 8, y + 10, 34, 42, 70,
                                  filled=True)
            # 램프
            pico2d.draw_circle(x, y + 118, 30, color[0], color[1], color[2],
                               30 if cp.active else 12, filled=True)
            pico2d.draw_circle(x, y + 118, 10, color[0], color[1], color[2],
                               255, filled=True)
            pico2d.draw_rectangle(x - 10, y + 104, x + 10, y + 110,
                                  18, 22, 42, filled=True)
            if cp.active:
                flicker = 2 + int(2 * abs(math.sin(time * 7 + cp.x)))
                pico2d.draw_circle(x, y + 118, 5 + flicker, 240, 255, 250,
                                   255, filled=True)

    def draw_goal(self, camera_x, time, shake_x=0.0):
        x = self.goal_x - camera_x + shake_x
        if x < -140 or x > WIDTH + 140:
            return
        cy = self.goal_y + 108
        pulse = 1.0 + 0.04 * math.sin(time * 3.0)
        # 빛무리
        pico2d.draw_circle(x, cy, int(100 * pulse), 80, 240, 220, 20,
                           filled=True)
        pico2d.draw_circle(x, cy, int(76 * pulse), 80, 240, 220, 30,
                           filled=True)
        # 포탈 고리
        for radius, alpha in ((82, 90), (72, 160), (62, 210)):
            for j in range(2):
                pico2d.draw_circle(x, cy, radius + j, 130, 250, 235, alpha)
        # 회전하는 불꽃
        for i in range(12):
            angle = time * 1.6 + i * math.tau / 12.0
            px = x + math.cos(angle) * 70
            py = cy + math.sin(angle) * 70
            pico2d.draw_circle(px, py, 4, 190, 255, 245, 220, filled=True)
        # 바닥
        pico2d.draw_rectangle(x - 42, self.goal_y - 6, x + 42,
                              self.goal_y + 8, 34, 60, 80, filled=True)

    def draw_coins(self, camera_x, time, shake_x=0.0):
        for coin in self.coins:
            if coin.taken:
                continue
            x = coin.x - camera_x + shake_x
            if x < -30 or x > WIDTH + 30:
                continue
            y = coin.y + math.sin(time * 4.0 + coin.phase) * 5
            pico2d.draw_circle(x, y, 18, 255, 200, 80, 26, filled=True)
            pico2d.draw_circle(x, y, 11, 255, 206, 74, 255, filled=True)
            pico2d.draw_circle(x, y + 1, 6, 255, 242, 170, 255, filled=True)
            pico2d.draw_line(x - 5, y + 5, x + 2, y + 12, 255, 255, 230, 200)

    def draw_hearts(self, camera_x, time, shake_x=0.0):
        for heart in self.hearts:
            if heart.taken:
                continue
            x = heart.x - camera_x + shake_x
            if x < -40 or x > WIDTH + 40:
                continue
            y = heart.y + math.sin(time * 3.0 + heart.phase) * 6
            pico2d.draw_circle(x, y, 24, 255, 90, 130, 30, filled=True)
            draw_heart_shape(x, y, 30, (255, 92, 128))
            draw_heart_shape(x - 6, y + 5, 10, (255, 210, 220))

    # ------------------------------------------------------------------
    # HUD / 화면 효과
    # ------------------------------------------------------------------
    def draw_motes(self, motes):
        for x, y, speed, radius, phase in motes:
            alpha = 26 + int(18 * abs(math.sin(phase * 3)))
            pico2d.draw_circle(x, y, radius, 180, 210, 255, alpha,
                               filled=True)


def draw_heart_shape(cx, cy, size, color, filled=True):
    """도형으로 그리는 하트(하트 픽업과 HUD 에 같이 사용)."""
    if filled:
        pico2d.draw_circle(cx - size * 0.28, cy + size * 0.18,
                           size * 0.28, color[0], color[1], color[2],
                           255, filled=True)
        pico2d.draw_circle(cx + size * 0.28, cy + size * 0.18,
                           size * 0.28, color[0], color[1], color[2],
                           255, filled=True)
        steps = 12
        for i in range(steps):
            t = i / steps
            half = size * 0.6 * (1.0 - t)
            y = cy + size * 0.2 - size * 0.72 * t
            pico2d.draw_line(cx - half, y, cx + half, y,
                             color[0], color[1], color[2], 255)
    else:
        pico2d.draw_circle(cx - size * 0.28, cy + size * 0.18,
                           size * 0.28, color[0], color[1], color[2], 255,
                           filled=False)
        pico2d.draw_circle(cx + size * 0.28, cy + size * 0.18,
                           size * 0.28, color[0], color[1], color[2], 255,
                           filled=False)
        pico2d.draw_line(cx - size * 0.55, cy + size * 0.12,
                         cx, cy - size * 0.55,
                         color[0], color[1], color[2], 255)
        pico2d.draw_line(cx + size * 0.55, cy + size * 0.12,
                         cx, cy - size * 0.55,
                         color[0], color[1], color[2], 255)


class Game:
    def __init__(self):
        self.text = TextRenderer()
        self.world = World()
        self.girl = Girl(160, GROUND)
        self.girl.limit_left = 24
        self.girl.limit_right = WORLD_W - 24

        self.state = "title"
        self.time = 0.0
        self.play_time = 0.0
        self.camera = 0.0
        self.shake = 0.0
        self.shake_x = 0.0

        self.score = 0
        self.coin_count = 0
        self.checkpoint = (160, GROUND)
        self.best_score = 0
        self.clear_bonus = 0

        self.particles = []
        self.slashes = []
        self.last_attack_id = 0
        self.dust_timer = 0.0

        rng = random.Random(5)
        self.motes = [
            [rng.uniform(0, WIDTH), rng.uniform(0, HEIGHT),
             rng.uniform(8, 26), rng.uniform(1.0, 2.6),
             rng.uniform(0, math.tau)]
            for _ in range(38)
        ]

        self.smoke = False
        self.smoke_time = 0.0
        self.smoke_jump_t = 0.6
        self.smoke_attack_t = 0.4
        self.smoke_hit = False
        self.smoke_dead = False
        self.smoke_log = []

    # ------------------------------------------------------------------
    def start(self):
        self.world = World()
        self.girl = Girl(160, GROUND)
        self.girl.limit_left = 24
        self.girl.limit_right = WORLD_W - 24
        self.girl.invuln = 0.0  # 시작할 때 깜빡이지 않도록
        self.state = "play"
        self.play_time = 0.0
        self.camera = 0.0
        self.shake = 0.0
        self.score = 0
        self.coin_count = 0
        self.checkpoint = (160, GROUND)
        self.clear_bonus = 0
        self.particles = []
        self.slashes = []
        self.last_attack_id = 0
        self.dust_timer = 0.0
        self.smoke_time = 0.0
        self.smoke_jump_t = 0.6
        self.smoke_attack_t = 0.4
        self.smoke_hit = False
        self.smoke_dead = False
        self.smoke_log = []

    def toggle_pause(self):
        if self.state == "play":
            self.state = "paused"
            self.girl.clear_keys()
        elif self.state == "paused":
            self.state = "play"

    # ------------------------------------------------------------------
    def update(self, dt):
        dt = min(dt, 0.05)
        self.time += dt
        self._update_motes(dt)

        if self.state == "title":
            if self.smoke and self.time > 0.7:
                self.start()
            return

        if self.state == "paused":
            return

        if self.state == "play":
            self._update_play(dt)
        else:
            self._update_effects(dt)

    def _update_motes(self, dt):
        for mote in self.motes:
            mote[1] += mote[2] * dt
            mote[0] += math.sin(self.time * 0.6 + mote[4]) * 8 * dt
            if mote[1] > HEIGHT + 10:
                mote[1] = -10
                mote[0] = random.uniform(0, WIDTH)
            if mote[0] < -10:
                mote[0] = WIDTH + 10
            elif mote[0] > WIDTH + 10:
                mote[0] = -10

    def _update_play(self, dt):
        self.play_time += dt
        if self.smoke:
            self._smoke_input(dt)

        self.girl.update(dt, self.world.platforms)

        # 카메라
        target = clamp(self.girl.x - WIDTH * 0.42, 0, WORLD_W - WIDTH)
        self.camera += (target - self.camera) * min(1.0, dt * 7.0)

        # 착지/점프/달리기 먼지
        if self.girl.just_jumped:
            self._dust(self.girl.x, self.girl.y, 6)
        if self.girl.just_landed:
            self._dust(self.girl.x, self.girl.y,
                       12 if self.girl.land_speed > 760.0 else 7)
        if self.girl.state == "run" and self.girl.on_ground:
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                self.dust_timer = 0.12
                self._dust(self.girl.x - self.girl.facing * 14,
                           self.girl.y, 2)

        for enemy in self.world.enemies:
            enemy.update(dt, self.time)

        self._check_attack()
        self._check_coins()
        self._check_hearts()
        self._check_checkpoints()
        self._check_goal()
        self._check_enemy_contact()
        self._check_fall()

        self._update_effects(dt)

        if self.girl.state == "retire" and self.girl.retire_done:
            self.state = "gameover"
            self.best_score = max(self.best_score, self.score)

    def _check_attack(self):
        hitbox = self.girl.attack_hitbox()
        if self.girl.attack_id != self.last_attack_id:
            self.last_attack_id = self.girl.attack_id
            self.slashes.append(
                Slash(self.girl.x, self.girl.y, self.girl.facing)
            )
            self.burst(
                self.girl.x + self.girl.facing * 60,
                self.girl.y + 95,
                (190, 245, 255), 3, 160, 0.25, 3, gravity=0,
            )
        if not hitbox:
            return
        for enemy in self.world.enemies:
            if not enemy.alive or enemy.last_attack == self.girl.attack_id:
                continue
            if overlaps(*hitbox, *enemy.rect()):
                enemy.alive = False
                enemy.last_attack = self.girl.attack_id
                self.score += 100
                self.shake = max(self.shake, 5.0)
                color = (160, 120, 255) if enemy.kind == "wisp" else (110, 75, 190)
                self.burst(enemy.x, enemy.y + enemy.height * 0.5, color,
                           14, 300, 0.55, 4)

    def _check_coins(self):
        for coin in self.world.coins:
            if coin.taken:
                continue
            if overlaps(*self.girl.rect(),
                        coin.x - 16, coin.y - 16, 32, 32):
                coin.taken = True
                self.coin_count += 1
                self.score += 10
                self.burst(coin.x, coin.y, (255, 220, 120),
                           8, 190, 0.45, 3, gravity=250)

    def _check_hearts(self):
        for heart in self.world.hearts:
            if heart.taken:
                continue
            if overlaps(*self.girl.rect(),
                        heart.x - 18, heart.y - 18, 36, 36):
                heart.taken = True
                if self.girl.hp < self.girl.MAX_HP:
                    self.girl.heal(1)
                else:
                    self.score += 50
                self.burst(heart.x, heart.y, (255, 110, 150),
                           14, 240, 0.6, 4, gravity=300)

    def _check_checkpoints(self):
        for cp in self.world.checkpoints:
            if cp.active:
                continue
            if abs(self.girl.x - cp.x) < 46 and self.girl.y <= cp.y + 150:
                cp.active = True
                self.checkpoint = (cp.x, cp.y + 2)
                self.girl.heal(1)
                self.burst(cp.x, cp.y + 110, (120, 250, 220),
                           22, 280, 0.7, 4, gravity=200)

    def _check_goal(self):
        if self.state != "play":
            return
        if abs(self.girl.x - self.world.goal_x) < 46:
            self.state = "clear"
            self.clear_bonus = int(max(0, 3000 - self.play_time * 25))
            self.score += self.clear_bonus
            self.best_score = max(self.best_score, self.score)
            self.shake = 8.0
            self.burst(self.world.goal_x, GROUND + 100,
                       (140, 255, 240), 40, 420, 0.9, 5, gravity=120)

    def _check_enemy_contact(self):
        gx, gy, gw, gh = self.girl.rect()
        for enemy in self.world.enemies:
            if not enemy.alive:
                continue
            ex, ey, ew, eh = enemy.rect()
            if not overlaps(gx, gy, gw, gh, ex, ey, ew, eh):
                continue
            stomp = (
                self.girl.vy < -80.0
                and self.girl.prev_y >= ey + eh - 16
                and self.girl.y <= ey + eh + 34
            )
            if stomp:
                enemy.alive = False
                self.girl.bounce(700.0)
                self.score += 150
                self.shake = max(self.shake, 6.0)
                color = (160, 120, 255) if enemy.kind == "wisp" else (110, 75, 190)
                self.burst(enemy.x, enemy.y + enemy.height * 0.5, color,
                           16, 300, 0.55, 4)
            else:
                if self.girl.take_hit(enemy.x):
                    self.shake = max(self.shake, 11.0)
                    self.burst(self.girl.x, self.girl.y + 100,
                               (255, 120, 140), 16, 320, 0.6, 4)
                    if self.girl.hp <= 0:
                        self.shake = 18.0
                        self.best_score = max(self.best_score, self.score)

    def _check_fall(self):
        if self.girl.state == "retire":
            # 사망 모션 중에는 낙하 판정을 하지 않는다.
            return
        if self.girl.y >= -80:
            return
        if self.girl.hp <= 1:
            self.girl.x, self.girl.y = self.checkpoint
            self.girl.die()
            self.shake = 18.0
            self.best_score = max(self.best_score, self.score)
        else:
            self.girl.hp -= 1
            self.girl.respawn(*self.checkpoint)
            self.shake = 14.0
            self.burst(self.checkpoint[0], self.checkpoint[1] + 60,
                       (140, 170, 255), 18, 300, 0.7, 4)

    def _update_effects(self, dt):
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

        for slash in self.slashes:
            slash.update(dt)
        self.slashes = [s for s in self.slashes if s.life > 0]

        if self.shake > 0.0:
            self.shake = max(0.0, self.shake - dt * 55.0)

    # ------------------------------------------------------------------
    def _smoke_input(self, dt):
        self.smoke_time += dt
        self.girl.keys.add("right")
        self.smoke_jump_t -= dt
        if self.smoke_jump_t <= 0.0:
            self.smoke_jump_t = 0.9
            self.girl.request_jump()
            self.girl.jump_held = True
        self.smoke_attack_t -= dt
        if self.smoke_attack_t <= 0.0:
            self.smoke_attack_t = 0.6
            self.girl.request_attack()
        if self.smoke_time > 2.0 and not self.smoke_hit:
            self.smoke_hit = True
            self.girl.take_hit(self.girl.x + 100)
        if self.smoke_time > 3.6 and not self.smoke_dead:
            self.smoke_dead = True
            self.girl.hp = 1
            self.girl.invuln = 0.0
            self.girl.take_hit(self.girl.x + 100)
        key = (self.state, self.girl.state)
        if not self.smoke_log or self.smoke_log[-1] != key:
            self.smoke_log.append(key)
            print("[smoke] state=%s girl=%s x=%.1f score=%d"
                  % (self.state, self.girl.state, self.girl.x, self.score))

    def burst(self, x, y, color, count=10, speed=260.0, life=0.6,
              radius=4, gravity=900.0):
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            velocity = random.uniform(speed * 0.3, speed)
            self.particles.append(
                Particle(
                    x, y,
                    math.cos(angle) * velocity,
                    math.sin(angle) * velocity + speed * 0.25,
                    random.uniform(life * 0.55, life),
                    random.uniform(radius * 0.6, radius * 1.5),
                    color,
                    gravity,
                )
            )

    def _dust(self, x, y, count):
        self.burst(x, y + 4, (120, 140, 190), count, 150, 0.4, 3,
                   gravity=180)

    # ------------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------------
    def draw(self):
        self.shake_x = random.uniform(-self.shake, self.shake) * 0.6

        self.world.draw_background(self.camera, self.time, self.shake_x)

        if self.state == "title":
            self._draw_title()
            return

        self._draw_world()
        self.world.draw_motes(self.motes)
        self._draw_hud()

        if self.state == "paused":
            self._draw_pause()
        elif self.state == "clear":
            self._draw_clear()
        elif self.state == "gameover":
            self._draw_gameover()

    def _draw_world(self):
        cam = self.camera
        shake = self.shake_x

        self.world.draw_platforms(cam, shake)
        self.world.draw_checkpoints(cam, self.time, shake)
        self.world.draw_goal(cam, self.time, shake)
        self.world.draw_coins(cam, self.time, shake)
        self.world.draw_hearts(cam, self.time, shake)

        for enemy in self.world.enemies:
            enemy.draw(cam, self.time, shake)

        self.girl.draw(cam, shake, self.time)

        for particle in self.particles:
            particle.draw(cam, shake)
        for slash in self.slashes:
            slash.draw(cam, shake)

    def _draw_hud(self):
        # 하트
        for i in range(Girl.MAX_HP):
            filled = i < self.girl.hp
            draw_heart_shape(38 + i * 38, HEIGHT - 52, 26,
                             (255, 92, 128) if filled else (66, 70, 100))
        self.text.draw(24, 30, HEIGHT - 96,
                       "SCORE %06d" % self.score, (230, 236, 250))
        # 코인
        pico2d.draw_circle(WIDTH - 156, HEIGHT - 56, 12, 255, 206, 74,
                           255, filled=True)
        pico2d.draw_circle(WIDTH - 156, HEIGHT - 55, 5, 255, 245, 190,
                           255, filled=True)
        self.text.draw(24, WIDTH - 134, HEIGHT - 56,
                       "x %02d" % self.coin_count, (240, 220, 150))
        minutes = int(self.play_time) // 60
        seconds = int(self.play_time) % 60
        self.text.draw(20, WIDTH - 134, HEIGHT - 96,
                       "TIME %02d:%02d" % (minutes, seconds),
                       (170, 190, 220))

        # 진행도
        bar_left, bar_right, bar_y = 430, 850, HEIGHT - 26
        pico2d.draw_line(bar_left, bar_y, bar_right, bar_y, 70, 78, 118)
        progress = clamp(self.girl.x / self.world.goal_x, 0.0, 1.0)
        px = bar_left + (bar_right - bar_left) * progress
        pico2d.draw_rectangle(bar_left, bar_y - 1, px, bar_y + 1,
                              60, 220, 190, filled=True)
        pico2d.draw_circle(px, bar_y, 5, 150, 255, 235, 255, filled=True)

        self.text.draw(16, 30, 26,
                       "A / D 이동   SPACE 점프   J 공격   P 일시정지",
                       (120, 136, 172), shadow=None)

    def _draw_title(self):
        # 무대
        pico2d.draw_rectangle(0, 0, WIDTH, GROUND, 15, 18, 38, filled=True)
        pico2d.draw_rectangle(0, GROUND - 7, WIDTH, GROUND,
                              62, 226, 196, filled=True)

        # 스포트라이트
        for radius, alpha in ((240, 14), (180, 20), (120, 26)):
            pico2d.draw_circle(986, GROUND + 200, radius,
                               255, 210, 160, alpha, filled=True)

        frame = int(self.time / 0.13) % 10
        self.girl.draw_preview(986, GROUND + 8, 0.62, frame)

        title_x = 430
        pico2d.draw_circle(title_x, 500, 300, 120, 80, 200, 20, filled=True)
        pico2d.draw_circle(title_x, 500, 220, 120, 80, 200, 18, filled=True)
        self.text.draw(72, title_x, 520, "그림자 소녀",
                       (246, 242, 255), "center", shadow=(52, 20, 80))
        self.text.draw(22, title_x, 462, "S H A D O W   G I R L",
                       (140, 230, 230), "center")
        self.text.draw(19, title_x, 420,
                       "어둠이 삼킨 숲을 지나 빛의 문으로",
                       (170, 170, 215), "center")

        blink = abs(math.sin(self.time * 2.2))
        if blink > 0.25:
            self.text.draw(28, title_x, 330,
                           "SPACE 키를 눌러 시작",
                           (255, 236, 190), "center")

        self.text.draw(18, 60, 250,
                       "A / D  또는  ← / →    이동", (200, 210, 235))
        self.text.draw(18, 60, 218,
                       "SPACE / W / ↑         점프", (200, 210, 235))
        self.text.draw(18, 60, 186,
                       "J / X                 공격", (200, 210, 235))
        self.text.draw(18, 60, 154,
                       "P                     일시정지", (150, 160, 190))
        if self.best_score > 0:
            self.text.draw(18, WIDTH - 60, 40,
                           "BEST %06d" % self.best_score,
                           (220, 210, 160), align="right")

    def _draw_pause(self):
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 170,
                              filled=True)
        self.text.draw(56, WIDTH // 2, HEIGHT // 2 + 30, "PAUSED",
                       (235, 240, 255), "center")
        self.text.draw(20, WIDTH // 2, HEIGHT // 2 - 34,
                       "P 키를 눌러 계속", (160, 185, 220), "center")

    def _draw_clear(self):
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 165,
                              filled=True)
        self.text.draw(56, WIDTH // 2, HEIGHT // 2 + 120,
                       "STAGE CLEAR!", (130, 250, 225), "center")
        self.text.draw(26, WIDTH // 2, HEIGHT // 2 + 50,
                       "빛의 문을 통과했습니다", (225, 235, 250), "center")
        self.text.draw(24, WIDTH // 2, HEIGHT // 2 - 6,
                       "시간 보너스  +%d" % self.clear_bonus,
                       (230, 210, 140), "center")
        self.text.draw(30, WIDTH // 2, HEIGHT // 2 - 54,
                       "TOTAL SCORE  %06d" % self.score,
                       (245, 245, 255), "center")
        self.text.draw(20, WIDTH // 2, HEIGHT // 2 - 126,
                       "R 키를 눌러 다시 시작", (170, 200, 230), "center")

    def _draw_gameover(self):
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 180,
                              filled=True)
        self.text.draw(64, WIDTH // 2, HEIGHT // 2 + 90, "GAME OVER",
                       (255, 110, 130), "center")
        self.text.draw(24, WIDTH // 2, HEIGHT // 2 + 18,
                       "SCORE  %06d" % self.score, (230, 235, 250),
                       "center")
        self.text.draw(20, WIDTH // 2, HEIGHT // 2 - 56,
                       "R 키를 눌러 다시 시작", (175, 195, 225), "center")


# ---------------------------------------------------------------------------
def main():
    smoke = "--smoke" in sys.argv

    pico2d.open_canvas(WIDTH, HEIGHT)
    pico2d.hide_cursor()
    pico2d.hide_lattice()
    enable_alpha_blending()
    patch_draw_primitives()

    game = Game()
    game.smoke = smoke

    last = pico2d.get_time()
    running = True

    while running:
        now = pico2d.get_time()
        dt = min(max(now - last, 0.0), 0.05)
        last = now

        for ev in pico2d.get_events():
            if ev.type == sdl2.SDL_QUIT:
                running = False
            elif ev.type == sdl2.SDL_KEYDOWN:
                if ev.key == sdl2.SDLK_ESCAPE:
                    running = False
                elif ev.key == sdl2.SDLK_p and game.state in ("play", "paused"):
                    game.toggle_pause()
                elif game.state == "play":
                    if ev.key == sdl2.SDLK_r:
                        game.start()
                    else:
                        game.girl.handle_event(ev)
                elif game.state in ("title", "clear", "gameover"):
                    if ev.key in (sdl2.SDLK_SPACE, sdl2.SDLK_RETURN,
                                  sdl2.SDLK_r):
                        game.start()
            elif ev.type == sdl2.SDL_KEYUP:
                game.girl.handle_event(ev)
            elif (ev.type == sdl2.SDL_MOUSEBUTTONDOWN
                  and ev.button == sdl2.SDL_BUTTON_LEFT
                  and game.state == "play"):
                game.girl.request_attack()

        game.update(dt)
        game.draw()
        pico2d.update_canvas()

        if smoke and game.time > 7.0:
            print("[smoke] finished state=%s girl=%s score=%d coins=%d x=%.1f"
                  % (game.state, game.girl.state, game.score,
                     game.coin_count, game.girl.x))
            running = False

    pico2d.close_canvas()


if __name__ == "__main__":
    main()
