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
import time

import pico2d
import sdl2

from background import Background
from bear import ATTACK_DURATION as BEAR_ATTACK_DURATION
from bear import BEAR_HEIGHT, BEAR_WIDTH, draw_bear
from bird import (ATTACK_DURATION as BIRD_ATTACK_DURATION, ATTACK_HOLD,
                  BIRD_HEIGHT, BIRD_WIDTH, DEATH_TIME, FALL_TIME, draw_bird)
from fence import Fence
from girl import Girl
from lamp import Lamp
from punch import DURATION as PUNCH_DURATION
from punch import draw_punch
from bench import Bench
from box import Box
from road import Road

WIDTH, HEIGHT = 1280, 720
GROUND = 140
# 공중에 떠 있는 오브젝트(발판, 코인, 하트, 위습, 발판 위 슬라임)를 내리는 양(px).
# 바닥에 서 있는 것은 도로 윗면에 고정돼 있으므로 내리지 않는다.
FLOAT_DROP = 60
# 캐릭터와 땅 위의 적이 서는 높이. 도로 그림은 GROUND 에 그대로 둔다.
STAND_Y = GROUND - FLOAT_DROP
WORLD_W = 7000
FPS = 60

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_FILE = os.path.join(BASE_DIR, "sprites", "object", "background.png")
BG_OVERLAY_FILE = os.path.join(BASE_DIR, "sprites", "object", "background_black.png")
ROAD_FILE = os.path.join(BASE_DIR, "sprites", "object", "road.png")
FENCE_FILE = os.path.join(BASE_DIR, "sprites", "object", "fence2.png")
# 벤치와 상자의 개수, 그리고 가구 사이 최소 간격(px)과 배치 가능한 x 범위
BENCH_COUNT = 10
BOX_COUNT = 6
FURNITURE_GAP = 40
FURNITURE_MIN_X = 700
FURNITURE_MAX_X = 6200
# 코인/회복 아이템 배치
COIN_TOTAL = 40  # 전체 코인 개수
HEART_COUNT = 3  # 회복 아이템 개수
HEART_MIN_SEGMENT = 2  # 회복 아이템은 이 번째 땅(0부터 셈, 3번째 땅)부터 나온다
PICKUP_LIFT = 50  # 윗면에서 코인/아이템까지의 높이
PIT_ARC_COUNT = 2  # 코인 포물선을 놓을 구멍 개수
PIT_ARC_BASE = GROUND + 40  # 포물선 시작/끝 높이
PIT_ARC_HEIGHT = 80  # 포물선 꼭대기까지 올라가는 높이

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


# ---------------------------------------------------------------------------
# 미리 구운 텍스처
# ---------------------------------------------------------------------------
class Art:
    """도형/글자를 텍스처로 미리 구워 프레임당 그리기 호출 수를 줄인다.

    SDL 의 draw_circle 은 채운 원 하나를 수십 번의 draw_line 으로 그린다.
    (소프트웨어 렌더러나 원격 데스크톱 환경에서는 이 호출 하나하나가 비싸다.)
    같은 모양을 매 프레임 다시 그리는 대신 한 번만 구워 두고 텍스처로 찍으면
    화면에 보이는 결과는 거의 같으면서 그리기 비용은 크게 줄어든다.
    """

    DISC = 64  # 원/발광 텍스처 해상도

    def __init__(self):
        self.renderer = pico2d.pico2d.renderer
        self._images = {}
        self._texts = {}

    # -- 텍스처 굽기 ----------------------------------------------------
    def bake(self, key, width, height, paint):
        image = self._images.get(key)
        if image is not None:
            return image
        width = max(1, int(width))
        height = max(1, int(height))
        texture = pico2d.SDL_CreateTexture(
            self.renderer,
            pico2d.SDL_PIXELFORMAT_RGBA8888,
            pico2d.SDL_TEXTUREACCESS_TARGET,
            width,
            height,
        )
        pico2d.SDL_SetTextureBlendMode(texture, pico2d.SDL_BLENDMODE_BLEND)
        try:
            pico2d.SDL_SetTextureScaleMode(texture, pico2d.SDL_ScaleModeLinear)
        except Exception:
            pass
        pico2d.SDL_SetRenderTarget(self.renderer, texture)
        pico2d.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 0)
        pico2d.SDL_RenderClear(self.renderer)
        # pico2d 의 도형 함수는 y 를 전역 canvas_height 기준으로 뒤집는다.
        # 작은 텍스처에 구울 때는 그 높이를 잠시 바꿔 좌표를 텍스처 기준으로
        # 맞춘다. (그러지 않으면 그림이 텍스처 밖으로 나가 빈 텍스처가 된다.)
        module = pico2d.pico2d
        saved_height = module.canvas_height
        module.canvas_height = height
        try:
            paint()
        finally:
            module.canvas_height = saved_height
            pico2d.SDL_SetRenderTarget(self.renderer, None)
        image = pico2d.Image(texture)
        self._images[key] = image
        return image

    # -- 그리기 ---------------------------------------------------------
    def blit(self, image, x, y, width=None, height=None, alpha=255):
        """이미지를 (x, y) 중심으로 그린다. (y 는 화면 좌표계)"""
        if image is None:
            return
        if width is None:
            width = image.w
        if height is None:
            height = image.h
        mod = max(0, min(255, int(alpha)))
        if getattr(image, "_art_alpha", None) != mod:
            pico2d.SDL_SetTextureAlphaMod(image.texture, mod)
            image._art_alpha = mod
        rect = pico2d.SDL_Rect(
            int(x - width * 0.5),
            int(HEIGHT - y - height * 0.5),
            int(width),
            int(height),
        )
        pico2d.SDL_RenderCopy(self.renderer, image.texture, None, rect)

    def blit_to(self, image, left, bottom, width=None, height=None, alpha=255):
        """이미지를 왼쪽 아래 (left, bottom) 기준으로 그린다."""
        if width is None:
            width = image.w
        if height is None:
            height = image.h
        self.blit(image, left + width * 0.5, bottom + height * 0.5,
                  width, height, alpha)

    # -- 원 / 발광 ------------------------------------------------------
    def disc(self, color, glow=False):
        color = tuple(int(c) for c in color)
        key = ("disc", color, glow)
        image = self._images.get(key)
        if image is not None:
            return image

        size = self.DISC
        radius = size * 0.5 - 1.0
        cx = cy = size * 0.5

        def paint():
            if glow:
                # 바깥으로 갈수록 투명해지는 부드러운 발광.
                for r in range(int(radius), 0, -1):
                    t = r / radius
                    a = int(255 * (1.0 - t) ** 2)
                    if a > 0:
                        pico2d.draw_circle(cx, cy, r, color[0], color[1],
                                           color[2], a, filled=True)
            else:
                # 바깥 1~2px 만 반투명하게 해서 축소해도 각져 보이지 않게.
                for r in range(int(radius), 0, -1):
                    t = r / radius
                    if t > 0.86:
                        a = int(255 * (1.0 - t) / 0.14)
                    else:
                        a = 255
                    if a > 0:
                        pico2d.draw_circle(cx, cy, r, color[0], color[1],
                                           color[2], a, filled=True)

        image = self.bake(key, size, size, paint)
        return image

    # -- 글자 -----------------------------------------------------------
    def text(self, font, size, text, color):
        color = tuple(int(c) for c in color)
        key = (size, text, color)
        image = self._texts.get(key)
        if image is not None:
            return image
        if len(self._texts) > 640:
            # 점수/시간처럼 계속 바뀌는 문자열이 쌓이는 것을 막는다.
            self._texts.clear()
        sdl_color = pico2d.SDL_Color(color[0], color[1], color[2])
        surface = pico2d.TTF_RenderUTF8_Blended(
            font.font, text.encode("utf-8"), sdl_color
        )
        if not surface:
            return None
        texture = pico2d.SDL_CreateTextureFromSurface(self.renderer, surface)
        pico2d.SDL_FreeSurface(surface)
        image = pico2d.Image(texture)
        try:
            pico2d.SDL_SetTextureScaleMode(texture, pico2d.SDL_ScaleModeLinear)
        except Exception:
            pass
        self._texts[key] = image
        return image


_ART = None


def art():
    global _ART
    if _ART is None:
        _ART = Art()
    return _ART


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
            self._draw(size, x + 2, y - 2, text, shadow)
        self._draw(size, x, y, text, color)

    def _draw(self, size, x, y, text, color):
        image = art().text(self.font(size), size, text, color)
        if image is not None:
            art().blit(image, x + image.w * 0.5, y)


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
        draw = art()
        image = draw.disc(self.color)
        draw.blit(
            image,
            self.x - camera_x + shake_x,
            self.y,
            radius * 2,
            radius * 2,
            alpha,
        )


class Slash:
    """공격 이펙트(punch_effect.png 10프레임을 한 번 재생)."""

    def __init__(self, girl, facing):
        self.girl = girl
        self.x = girl.x
        self.y = girl.y
        self.facing = facing
        self.elapsed = 0.0
        self.life = PUNCH_DURATION
        self.max_life = PUNCH_DURATION

    def update(self, dt):
        # 이펙트는 공격하는 동안 캐릭터를 따라 움직인다.
        self.x = self.girl.x
        self.y = self.girl.y
        self.elapsed += dt
        self.life -= dt

    def draw(self, camera_x, shake_x=0.0):
        if self.life <= 0:
            return
        draw_punch(self.x - camera_x + shake_x, self.y, self.facing, self.elapsed)

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
    WIDTH = {"bear": BEAR_WIDTH, "bird": BIRD_WIDTH}
    HEIGHT = {"bear": BEAR_HEIGHT, "bird": BIRD_HEIGHT}
    ATTACK_DURATION = {"bear": BEAR_ATTACK_DURATION, "bird": BIRD_ATTACK_DURATION}

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
        self.anim_time = 0.0
        self.attack_hold = 0.0  # 접촉 중이라는 표시(접촉이 끊기면 조금 뒤 0)
        self.attack_t = None  # 공격 모션 경과 시간(접촉 시작 시 0부터)
        self.death_time = 0.0
        self.death_y = self.y
        self.facing = -1

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

    def touch(self):
        """girl 과 닿는 순간 공격 모션을 한 번 재생한다. 접촉이 이어지는 동안은 다시 재생하지 않는다."""
        # 접촉이 막 시작됐고 이전 공격 모션이 끝난 경우에만 다시 재생한다.
        if self.attack_hold <= 0.0 and (
                self.attack_t is None
                or self.attack_t >= self.ATTACK_DURATION[self.kind]):
            self.attack_t = 0.0
        self.attack_hold = ATTACK_HOLD

    def kill(self):
        self.alive = False
        self.death_time = 0.0
        self.death_y = self.y

    def update(self, dt, time):
        self.anim_time += dt
        if not self.alive:
            self.death_time += dt
            if self.kind == "bird":
                # 사망 모션과 같은 시간 동안 지면(STAND_Y)까지 떨어진다.
                progress = min(1.0, self.death_time / FALL_TIME)
                self.y = self.death_y + (STAND_Y - self.death_y) * progress * progress
            return
        self.attack_hold = max(0.0, self.attack_hold - dt)
        if self.attack_t is not None:
            self.attack_t += dt
        if self.kind == "bear":
            self.x += self.vx * dt
            half = self.width * 0.5
            if self.x < self.left + half:
                self.x = self.left + half
                self.vx = abs(self.vx)
            elif self.x > self.right - half:
                self.x = self.right - half
                self.vx = -abs(self.vx)
            self.facing = 1 if self.vx >= 0 else -1
        else:
            swing = time * 1.1 + self.phase
            self.x = self.ax + math.sin(swing) * 42.0
            self.y = self.ay + math.sin(time * 2.4 + self.phase) * 16.0
            self.facing = 1 if math.cos(swing) >= 0.0 else -1

    def draw(self, camera_x, time, shake_x=0.0):
        if not self.alive and self.death_time > DEATH_TIME:
            return
        x = self.x - camera_x + shake_x
        if x < -80 or x > WIDTH + 80:
            return
        if not self.alive:
            state, t = "retire", self.death_time
        elif self.attack_t is not None and self.attack_t < self.ATTACK_DURATION[self.kind]:
            state, t = "attack", self.attack_t
        else:
            state, t = "walk", self.anim_time
        if self.kind == "bear":
            draw_bear(self.x, self.y, self.facing, state, t, camera_x, shake_x)
        else:
            draw_bird(self.x, self.y, self.facing,
                      "fly" if state == "walk" else state, t,
                      camera_x, shake_x)


class World:
    def __init__(self):
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.hearts = []
        self.checkpoints = []
        self.goal_x = 6720
        self.goal_y = GROUND
        self.background = Background(BG_FILE, BG_OVERLAY_FILE)
        self.road = Road(ROAD_FILE)
        self.lamp = Lamp()
        self.fence = Fence(FENCE_FILE)
        self.ground_spans = []
        self.furniture = []  # (종류, 그림 객체, 그림 중심 x)
        self._build()

    # ------------------------------------------------------------------
    def _add_ground(self, left, right):
        self.ground_spans.append((left, right))
        self.platforms.append(
            Platform(left, STAND_Y - 240, right - left, 240)
        )

    def _add_surface(self, left, top, width, height=24):
        # 벤치/상자의 윗면은 단방향 발판: 아래에서 점프해 올라가고, 위에서만 딛는다.
        self.platforms.append(
            Platform(left, top - height, width, height, one_way=True)
        )

    def _place_furniture(self, bench_count, box_count):
        """벤치와 상자를 땅 구간 위에 겹치지 않게 랜덤으로 놓는다."""
        box_half = Box(STAND_Y).size() * 0.5
        bench_half = Bench().size() * 0.5
        placed = []  # (중심 x, 반폭)

        def free(cx, half):
            for other, other_half in placed:
                if abs(cx - other) < half + other_half + FURNITURE_GAP:
                    return False
            for cp in self.checkpoints:
                if abs(cx - cp.x) < half + 60:
                    return False
            return True

        def pick(half):
            for _ in range(300):
                left, right = random.choice(self.ground_spans)
                lo = max(left + half, FURNITURE_MIN_X)
                hi = min(right - half, FURNITURE_MAX_X)
                if lo > hi:
                    continue
                cx = random.uniform(lo, hi)
                if free(cx, half):
                    placed.append((cx, half))
                    return cx
            return None

        for _ in range(box_count):
            cx = pick(box_half)
            if cx is not None:
                self.furniture.append(("high", Box(STAND_Y), cx))
        for _ in range(bench_count):
            cx = pick(bench_half)
            if cx is not None:
                self.furniture.append(("low", Bench(), cx))

    def _place_pickups(self):
        """코인과 회복 아이템을 겹치지 않게 놓는다.

        - 회복 아이템: 윗면 몇 곳에 하나씩. 그 윗면에는 코인을 놓지 않는다.
        - 코인 줄: 일부 윗면에만 놓는다.
        - 구멍 몇 곳: 점프 포물선을 따라 코인을 놓는다.
        """
        spans = sorted(self.ground_spans)
        gaps = [(a[1], b[0]) for a, b in zip(spans, spans[1:])]
        for left, right in random.sample(gaps, min(PIT_ARC_COUNT, len(gaps))):
            self._place_pit_arc(left, right)

        surfaces = [p for p in self.platforms if p.one_way]
        heart_min_x = spans[HEART_MIN_SEGMENT][0]
        heart_pool = [p for p in surfaces if p.left >= heart_min_x]
        heart_surfaces = random.sample(heart_pool, min(HEART_COUNT, len(heart_pool)))
        for plat in heart_surfaces:
            self.hearts.append(
                HeartPickup(plat.left + plat.width * 0.5, plat.top + PICKUP_LIFT,
                            random.random() * math.tau)
            )

        # 남은 코인 수만큼 윗면에 줄로 채운다(전체 COIN_TOTAL 개).
        budget = COIN_TOTAL - len(self.coins)
        random.shuffle(surfaces)
        for plat in surfaces:
            if budget <= 0:
                break
            if plat in heart_surfaces:
                continue
            count = min(budget, max(3, int(plat.width // 60)))
            spacing = (min(42.0, (plat.width - 40.0) / (count - 1))
                       if count > 1 else 0.0)
            center = plat.left + plat.width * 0.5
            for i in range(count):
                offset = (i - (count - 1) * 0.5) * spacing
                self.coins.append(
                    Coin(center + offset, plat.top + PICKUP_LIFT,
                         random.random() * math.tau)
                )
            budget -= count

    def _place_pit_arc(self, left, right):
        """구멍 위로 뛰어넘는 포물선을 따라 코인을 놓는다."""
        count = 7
        x0, x1 = left - 20, right + 20
        for i in range(count):
            t = i / (count - 1)
            x = x0 + (x1 - x0) * t
            y = PIT_ARC_BASE + 4 * PIT_ARC_HEIGHT * t * (1 - t)
            self.coins.append(Coin(x, y, random.random() * math.tau))

    def _add_surfaces(self):
        """가구의 밟을 수 있는 윗면을 발판으로 만든다."""
        for kind, prop, cx in self.furniture:
            if kind == "low":
                left, width, top = prop.seat_surface(GROUND)
                self._add_surface(cx + left, top, width)
            else:
                for level in (1, 2):
                    left, width, top = prop.level_surface(level)
                    self._add_surface(cx + left, top, width)

    def _add_coin(self, x, y):
        self.coins.append(
            Coin(x, y - FLOAT_DROP, random.random() * math.tau)
        )

    def _coin_line(self, x1, x2, y, step=50):
        x = x1
        while x <= x2:
            self._add_coin(x, y)
            x += step

    def _add_bear(self, x, ground_y, left, right):
        self.enemies.append(
            Enemy("bear", x, ground_y, left, right, random.random() * math.tau)
        )

    def _add_bear_on_surface(self):
        candidates = [p for p in self.platforms if p.one_way and p.width >= 150]
        plat = random.choice(candidates)
        self.enemies.append(
            Enemy("bear", plat.left + plat.width * 0.5, plat.top,
                  plat.left, plat.right, random.random() * math.tau)
        )

    def _add_bird(self, x, y):
        self.enemies.append(
            Enemy("bird", x, y - FLOAT_DROP, x - 50, x + 50,
                  random.random() * math.tau)
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

        # 체크포인트
        self.checkpoints = [Checkpoint(2000, GROUND), Checkpoint(4500, GROUND)]

        # 벤치(6개)와 상자(7개)를 랜덤으로 배치하고, 그 윗면을 발판으로 만든다.
        self._place_furniture(BENCH_COUNT, BOX_COUNT)
        self._add_surfaces()

        # 시작 지점 코인 줄 (발판과 무관하게 점프로 바로 닿는 높이)
        self._coin_line(180, 400, 200)

        # 벤치/상자 윗면 위의 코인과 회복 아이템
        self._place_pickups()

        # 슬라임
        self._add_bear(780, STAND_Y, 700, 1500)
        self._add_bear(1250, STAND_Y, 1150, 1490)
        self._add_bear(1750, STAND_Y, 1640, 1900)
        self._add_bear(2450, STAND_Y, 2300, 2650)
        self._add_bear(2810, STAND_Y, 2700, 2890)
        self._add_bear(3250, STAND_Y, 3040, 3400)
        self._add_bear(3600, STAND_Y, 3450, 3700)
        self._add_bear(3960, STAND_Y, 3800, 4180)
        self._add_bear(4550, STAND_Y, 4360, 4700)
        self._add_bear(5050, STAND_Y, 4900, 5200)
        self._add_bear(5450, STAND_Y, 5300, 5490)
        self._add_bear(5900, STAND_Y, 5660, 6000)
        self._add_bear(6300, STAND_Y, 6120, 6500)
        self._add_bear(6600, STAND_Y, 6500, 6880)
        # 벤치/상자 위 슬라임
        for _ in range(4):
            self._add_bear_on_surface()

        # 위습(날아다니는 적)
        self._add_bird(1350, 300)
        self._add_bird(2200, 430)
        self._add_bird(3200, 330)
        self._add_bird(4300, 350)
        self._add_bird(5000, 430)
        self._add_bird(5750, 320)
        self._add_bird(6450, 400)

    # ------------------------------------------------------------------
    # 배경
    # ------------------------------------------------------------------
    def draw_background(self, camera_x, time, shake_x=0.0):
        self.background.draw(art(), camera_x, shake_x)

    # ------------------------------------------------------------------
    # 발판
    # ------------------------------------------------------------------
    def draw_fence(self, camera_x, shake_x=0.0):
        a = art()
        for left, right in self.ground_spans:
            width = right - left
            x = left - camera_x + shake_x
            if x + width < -40 or x > WIDTH + 40:
                continue
            self.fence.draw(a, width, x, GROUND)

    def draw_platforms(self, camera_x, shake_x=0.0):
        a = art()
        # 레이어 순서: 땅 블록 < 벤치(낮은 발판) < 상자(높은 발판)
        for p in self.platforms:
            if p.one_way:
                continue
            x = p.left - camera_x + shake_x
            if x + p.width < -40 or x > WIDTH + 40:
                continue
            # 땅 블록의 물리 윗면은 STAND_Y 지만, 그림은 도로 윗면(GROUND)까지 그린다.
            height = p.height + FLOAT_DROP
            image = self.road.ground(a, p.left, p.bottom, p.width,
                                     height, GROUND, (18, 24, 46))
            a.blit_to(image, x, p.bottom, p.width, height)
        for kind in ("low", "high"):
            for furniture_kind, prop, cx in self.furniture:
                if furniture_kind != kind:
                    continue
                x = cx - camera_x + shake_x
                half = prop.size() * 0.5
                if x + half < -40 or x - half > WIDTH + 40:
                    continue
                prop.draw(a, x, GROUND)

    # ------------------------------------------------------------------
    # 체크포인트 / 골 / 아이템
    # ------------------------------------------------------------------
    def draw_checkpoints(self, camera_x, time, shake_x=0.0):
        a = art()
        for cp in self.checkpoints:
            x = cp.x - camera_x + shake_x
            if x < -120 or x > WIDTH + 120:
                continue
            self.lamp.draw(a, x, cp.y, cp.active)

    def _goal_images(self):
        def paint_glow():
            pico2d.draw_circle(110, 110, 100, 80, 240, 220, 20, filled=True)
            pico2d.draw_circle(110, 110, 76, 80, 240, 220, 30, filled=True)

        def paint_rings():
            for radius, alpha in ((82, 90), (72, 160), (62, 210)):
                for j in range(2):
                    pico2d.draw_circle(110, 110, radius + j,
                                       130, 250, 235, alpha)

        glow = art().bake("goal_glow", 220, 220, paint_glow)
        rings = art().bake("goal_rings", 220, 220, paint_rings)
        return glow, rings

    def draw_goal(self, camera_x, time, shake_x=0.0):
        x = self.goal_x - camera_x + shake_x
        if x < -140 or x > WIDTH + 140:
            return
        a = art()
        cy = self.goal_y + 108
        pulse = 1.0 + 0.04 * math.sin(time * 3.0)
        glow, rings = self._goal_images()
        # 빛무리
        a.blit(glow, x, cy, 220 * pulse, 220 * pulse)
        # 포탈 고리
        a.blit(rings, x, cy, 220, 220)
        # 회전하는 불꽃
        spark = a.disc((190, 255, 245))
        for i in range(12):
            angle = time * 1.6 + i * math.tau / 12.0
            px = x + math.cos(angle) * 70
            py = cy + math.sin(angle) * 70
            a.blit(spark, px, py, 8, 8)
        # 바닥
        pico2d.draw_rectangle(x - 42, self.goal_y - 6, x + 42,
                              self.goal_y + 8, 34, 60, 80, filled=True)

    def draw_coins(self, camera_x, time, shake_x=0.0):
        image = coin_image()
        a = art()
        for coin in self.coins:
            if coin.taken:
                continue
            x = coin.x - camera_x + shake_x
            if x < -30 or x > WIDTH + 30:
                continue
            y = coin.y + math.sin(time * 4.0 + coin.phase) * 5
            a.blit(image, x, y)

    def draw_hearts(self, camera_x, time, shake_x=0.0):
        image = heart_pickup_image()
        a = art()
        for heart in self.hearts:
            if heart.taken:
                continue
            x = heart.x - camera_x + shake_x
            if x < -40 or x > WIDTH + 40:
                continue
            y = heart.y + math.sin(time * 3.0 + heart.phase) * 6
            a.blit(image, x, y)

    # ------------------------------------------------------------------
    # HUD / 화면 효과
    # ------------------------------------------------------------------
    def draw_motes(self, motes):
        a = art()
        image = a.disc((180, 210, 255), glow=True)
        for x, y, speed, radius, phase in motes:
            alpha = 30 + int(22 * abs(math.sin(phase * 3)))
            a.blit(image, x, y, radius * 2, radius * 2, alpha)


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


def coin_image():
    """코인 그림(빛무리 + 몸통 + 하이라이트)을 한 장으로 굽는다."""
    def paint():
        cx = cy = 24
        pico2d.draw_circle(cx, cy, 18, 255, 200, 80, 26, filled=True)
        pico2d.draw_circle(cx, cy, 11, 255, 206, 74, 255, filled=True)
        pico2d.draw_circle(cx, cy + 1, 6, 255, 242, 170, 255, filled=True)
        pico2d.draw_line(cx - 5, cy + 5, cx + 2, cy + 12,
                         255, 255, 230, 200)

    return art().bake("coin", 48, 48, paint)


def heart_pickup_image():
    """하트 픽업 그림(빛무리 + 하트 + 하이라이트)을 한 장으로 굽는다."""
    def paint():
        pico2d.draw_circle(38, 38, 24, 255, 90, 130, 30, filled=True)
        draw_heart_shape(38, 38, 30, (255, 92, 128))
        draw_heart_shape(32, 43, 10, (255, 210, 220))

    return art().bake("heart_pickup", 76, 76, paint)


def hud_heart_image(filled):
    def paint():
        color = (255, 92, 128) if filled else (66, 70, 100)
        draw_heart_shape(32, 32, 26, color, filled=filled)

    return art().bake(("hud_heart", filled), 64, 64, paint)


class Game:
    def __init__(self):
        self.text = TextRenderer()
        self.world = World()
        self.girl = Girl(160, STAND_Y)
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
        self.checkpoint = (160, STAND_Y)
        self.best_score = 0
        self.clear_bonus = 0

        self.particles = []
        self.slashes = []
        self.last_attack_id = 0
        self.dust_timer = 0.0
        self.fps = 0.0
        self.renderer_name = ""

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
        self.girl = Girl(160, STAND_Y)
        self.girl.limit_left = 24
        self.girl.limit_right = WORLD_W - 24
        self.girl.invuln = 0.0  # 시작할 때 깜빡이지 않도록
        self.state = "play"
        self.play_time = 0.0
        self.camera = 0.0
        self.shake = 0.0
        self.score = 0
        self.coin_count = 0
        self.checkpoint = (160, STAND_Y)
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
                Slash(self.girl, self.girl.facing)
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
                enemy.kill()
                enemy.last_attack = self.girl.attack_id
                self.score += 100
                self.shake = max(self.shake, 5.0)
                color = (160, 120, 255) if enemy.kind == "bird" else (110, 75, 190)
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
                enemy.kill()
                self.girl.bounce(700.0)
                self.score += 150
                self.shake = max(self.shake, 6.0)
                color = (160, 120, 255) if enemy.kind == "bird" else (110, 75, 190)
                self.burst(enemy.x, enemy.y + enemy.height * 0.5, color,
                           16, 300, 0.55, 4)
            else:
                enemy.touch()
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

        self.world.draw_fence(cam, shake)
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
        a = art()
        # 하트
        for i in range(Girl.MAX_HP):
            a.blit(hud_heart_image(i < self.girl.hp), 38 + i * 38,
                   HEIGHT - 52)
        self.text.draw(24, 30, HEIGHT - 96,
                       "SCORE %06d" % self.score, (230, 236, 250))
        # 코인
        a.blit(coin_image(), WIDTH - 156, HEIGHT - 56, 28, 28)
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
        a.blit(a.disc((150, 255, 235)), px, bar_y, 10, 10)

        self.text.draw(16, 30, 26,
                       "A / D 이동   SPACE 점프   J 공격   P 일시정지",
                       (120, 136, 172), shadow=None)
        self._draw_fps(WIDTH - 24, HEIGHT - 26, align="right")

    def _draw_fps(self, x, y, align="left"):
        if self.fps <= 0.0:
            return
        color = (140, 230, 190) if self.fps >= 50.0 else (255, 190, 120)
        self.text.draw(16, x, y, "FPS %d" % round(self.fps), color,
                       align=align, shadow=None)

    def _spotlight_image(self):
        def paint():
            pico2d.draw_circle(240, 240, 240, 255, 210, 160, 14, filled=True)
            pico2d.draw_circle(240, 240, 180, 255, 210, 160, 20, filled=True)
            pico2d.draw_circle(240, 240, 120, 255, 210, 160, 26, filled=True)

        return art().bake("spotlight", 480, 480, paint)

    def _title_glow_image(self):
        def paint():
            pico2d.draw_circle(300, 300, 300, 120, 80, 200, 20, filled=True)
            pico2d.draw_circle(300, 300, 220, 120, 80, 200, 18, filled=True)

        return art().bake("title_glow", 600, 600, paint)

    def _draw_title(self):
        a = art()
        # 무대 (플레이 화면과 같은 바닥 그림)
        pico2d.draw_rectangle(0, 0, WIDTH, GROUND, 18, 24, 46, filled=True)
        self.world.road.draw_top(a, 0, GROUND)

        # 스포트라이트
        a.blit(self._spotlight_image(), 986, GROUND + 200)

        frame = int(self.time / 0.13)
        self.girl.draw_preview(986, STAND_Y + 8, 0.62, frame)

        title_x = 430
        a.blit(self._title_glow_image(), title_x, 500)
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
        self._draw_fps(WIDTH - 24, 26, align="right")
        if self.renderer_name:
            self.text.draw(14, WIDTH - 24, 8,
                           "renderer: %s" % self.renderer_name,
                           (110, 120, 150), align="right", shadow=None)

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
def force_software_renderer():
    """SDL 의 소프트웨어 렌더러를 강제한다. (--software, 성능 확인용)"""
    original = pico2d.pico2d.SDL_CreateRenderer

    def create(window, index, flags):
        if flags & pico2d.SDL_RENDERER_ACCELERATED:
            flags = pico2d.SDL_RENDERER_SOFTWARE
        return original(window, index, flags)

    pico2d.pico2d.SDL_CreateRenderer = create


def renderer_name():
    try:
        info = pico2d.SDL_RendererInfo()
        pico2d.SDL_GetRendererInfo(pico2d.pico2d.renderer, info)
        return info.name.decode("utf-8", "replace")
    except Exception:
        return "unknown"


def main():
    smoke = "--smoke" in sys.argv
    uncapped = "--uncapped" in sys.argv
    if "--software" in sys.argv:
        force_software_renderer()

    pico2d.open_canvas(WIDTH, HEIGHT)
    pico2d.hide_cursor()
    pico2d.hide_lattice()
    enable_alpha_blending()
    patch_draw_primitives()

    name = renderer_name()
    print("[renderer] %s%s" % (name, " (software forced)"
                               if "--software" in sys.argv else ""))

    game = Game()
    game.smoke = smoke
    game.renderer_name = name

    last = pico2d.get_time()
    running = True
    fps_frames = 0
    fps_clock = time.perf_counter()
    frame_target = 1.0 / (FPS + 2.0)

    while running:
        frame_start = time.perf_counter()
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

        fps_frames += 1
        fps_elapsed = time.perf_counter() - fps_clock
        if fps_elapsed >= 0.5:
            game.fps = fps_frames / fps_elapsed
            fps_frames = 0
            fps_clock = time.perf_counter()

        if smoke and game.time > 7.0:
            print("[smoke] finished state=%s girl=%s score=%d coins=%d x=%.1f"
                  % (game.state, game.girl.state, game.score,
                     game.coin_count, game.girl.x))
            print("[smoke] fps=%.1f renderer=%s" % (game.fps, name))
            running = False

        # 60fps 목표로 프레임 제한 (CPU/발열 감소)
        if not uncapped:
            remain = frame_target - (time.perf_counter() - frame_start)
            if remain > 0.001:
                time.sleep(remain)

    pico2d.close_canvas()


if __name__ == "__main__":
    main()
