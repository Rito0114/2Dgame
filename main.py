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
from cat import ATTACK_DURATION as CAT_ATTACK_DURATION
from cat import FIRE_TIME as CAT_FIRE_TIME
from cat import SHOT_INTERVAL as CAT_SHOT_INTERVAL
from cat import Bullet, muzzle
from cat import CAT_HEIGHT, CAT_WIDTH, draw_attack, draw_retire, draw_walk
from bird import (ATTACK_DURATION as BIRD_ATTACK_DURATION, ATTACK_HOLD,
                  BIRD_HEIGHT, BIRD_WIDTH, DEATH_TIME, FALL_TIME, draw_bird)
from fence import Fence
from dash import SkillBackground
from girl import Girl
from stage1 import SPEC as STAGE1_SPEC
from stage2 import SPEC as STAGE2_SPEC
from stage3 import SPEC as STAGE3_SPEC
from boss import Boss
from item import Coin, HeartPickup, coin_image
from lamp import Lamp
from lobby import Lobby
from bomb import BombField
import audio
from audio import Bgm, Sfx
from ui import HUDOverlay, kill_icon, skill_icon_center
from punch import DURATION as PUNCH_DURATION
from punch import PunchImpact, draw_punch
from bench import Bench
from box import Box
from road import Road
import story

WIDTH, HEIGHT = 1280, 720
GROUND = 140
# 공중에 떠 있는 오브젝트(발판, 코인, 하트, 위습, 발판 위 슬라임)를 내리는 양(px).
# 바닥에 서 있는 것은 도로 윗면에 고정돼 있으므로 내리지 않는다.
FLOAT_DROP = 60
# 캐릭터와 땅 위의 적이 서는 높이. 도로 그림은 GROUND 에 그대로 둔다.
STAND_Y = GROUND - FLOAT_DROP
FPS = 60
PAUSE_ITEMS = ("resume", "options", "quit")
OPTION_ITEMS = ("bgm", "sfx", "mute", "back")
DEV_ITEMS = ("invincible", "free_stage", "no_cooldown")
VOLUME_STEP = max(1, audio.MAX_VOLUME // 20)  # 슬라이드 한 칸 = 5%
# 예시 PNG에서 측정한 대사 위치(1920x1080 → 1280x720).
STORY_TEXT_X = 373
STORY_TEXT_Y = 130
STORY_TEXT_SIZE = 26
STORY_LINE_GAP = 30
STORY_TEXT_WIDTH = 820
# 대사 종료 후 대화 UI 가 사라지고 스테이지 제목이 나타나는 연출.
STORY_UI_FADE_TIME = 1.10
STAGE_TITLE_FADE_IN = 0.35
STAGE_TITLE_HOLD = 1.60
STAGE_TITLE_LARGE_SIZE = 64
STAGE_TITLE_SMALL_SIZE = 26
WARNING_TEXT = "WARNING"
WARNING_SIZE = 96
# 팝업이 뜨자마자 연속 입력으로 닫히지 않도록 짧게 입력을 막는다.
SKILL_POPUP_INPUT_DELAY = 0.35

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 벤치와 상자의 개수, 그리고 가구 사이 최소 간격(px)과 배치 가능한 x 범위
FURNITURE_GAP = 40
# 체크포인트가 활성화되는 세로 범위(체크포인트 기준 위쪽 px)
CHECKPOINT_REACH_Y = 300
# 코인/회복 아이템 배치
PICKUP_LIFT = 50  # 윗면에서 코인/아이템까지의 높이
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


def in_rect(x, y, rect):
    """(left, bottom, width, height) 안에 점이 있는지."""
    left, bottom, width, height = rect
    return left <= x <= left + width and bottom <= y <= bottom + height


def hit_index(rects, x, y):
    """여러 사각형 중 점이 들어간 첫 번째 인덱스."""
    for i, rect in enumerate(rects):
        if in_rect(x, y, rect):
            return i
    return None


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
        self._paints = {}
        self._texts = {}
        # 전체 화면 전환 때 논리 크기(WIDTH x HEIGHT)를 쓰면 여기 적어 둔다.
        self.logical = None

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
        self._paint(texture, width, height, paint)
        image = pico2d.Image(texture)
        self._images[key] = image
        self._paints[key] = (texture, width, height, paint)
        return image

    def _paint(self, texture, width, height, paint):
        if self.logical:
            sdl2.SDL_RenderSetLogicalSize(self.renderer, 0, 0)
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
            if self.logical:
                sdl2.SDL_RenderSetLogicalSize(self.renderer, *self.logical)

    def repaint_all(self):
        """화면 모드가 바뀌면 렌더 대상 텍스처의 내용이 사라지므로 다시 그린다."""
        for texture, width, height, paint in self._paints.values():
            self._paint(texture, width, height, paint)

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

class Checkpoint:
    __slots__ = ("x", "y", "active")

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.active = False


def death_sound(enemy):
    """곰은 곰 사망음, 고양이와 새는 새 사망음."""
    if enemy.kind == "bear":
        return "bear_deathsound.mp3"
    return "bird_deathsound.mp3"


class Enemy:
    WIDTH = {"bear": BEAR_WIDTH, "bird": BIRD_WIDTH, "cat": CAT_WIDTH}
    HEIGHT = {"bear": BEAR_HEIGHT, "bird": BIRD_HEIGHT, "cat": CAT_HEIGHT}
    ATTACK_DURATION = {"bear": BEAR_ATTACK_DURATION, "bird": BIRD_ATTACK_DURATION, "cat": CAT_ATTACK_DURATION}

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
        self.was_visible = False  # 고양이: 지난 프레임에 화면에 있었는지
        self.fired = False  # 고양이: 이번 공격에서 총알을 쐈는지
        self.next_shot = None  # 고양이: 다음 발사 예정 시각(게임 시간). 처음에는 None
        self.fall_target = STAND_Y  # 새: 쓰러져 떨어질 y. 구덩이 위면 화면 아래로 떨어진다.

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

    def is_attacking(self):
        return self.attack_t is not None and self.attack_t < self.ATTACK_DURATION[self.kind]

    def begin_attack(self):
        self.attack_t = 0.0
        self.fired = False

    def touch(self):
        """girl 과 닿는 순간 공격 모션을 한 번 재생한다. 접촉이 이어지는 동안은 다시 재생하지 않는다."""
        # 접촉이 막 시작됐고 이전 공격 모션이 끝난 경우에만 다시 재생한다.
        if self.attack_hold <= 0.0 and not self.is_attacking():
            self.begin_attack()
        self.attack_hold = ATTACK_HOLD

    def kill(self, fall_target=STAND_Y):
        self.alive = False
        self.death_time = 0.0
        self.death_y = self.y
        self.fall_target = fall_target

    def update(self, dt, time):
        self.anim_time += dt
        if not self.alive:
            self.death_time += dt
            if self.kind == "bird":
                # 사망 모션과 같은 시간 동안 지면(STAND_Y)까지 떨어진다.
                progress = min(1.0, self.death_time / FALL_TIME)
                self.y = self.death_y + (self.fall_target - self.death_y) * progress * progress
            return
        self.attack_hold = max(0.0, self.attack_hold - dt)
        if self.attack_t is not None:
            self.attack_t += dt
        if self.kind in ("bear", "cat"):
            if not (self.kind == "cat" and self.is_attacking()):
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
        if self.kind == "cat":
            if state == "retire":
                draw_retire(self.x, self.y, self.facing, t, camera_x, shake_x)
            elif state == "attack":
                draw_attack(self.x, self.y, self.facing, t, camera_x, shake_x)
            else:
                draw_walk(self.x, self.y, self.facing, t, camera_x, shake_x)
        elif self.kind == "bear":
            draw_bear(self.x, self.y, self.facing, state, t, camera_x, shake_x)
        else:
            draw_bird(self.x, self.y, self.facing,
                      "fly" if state == "walk" else state, t,
                      camera_x, shake_x)


STAGES = {1: STAGE1_SPEC, 2: STAGE2_SPEC, 3: STAGE3_SPEC}


class World:
    def __init__(self, spec):
        self.spec = spec
        self.world_w = spec.world_w
        self.platforms = []
        self.enemies = []
        self.coins = []
        self.hearts = []
        self.checkpoints = []
        self.goal_x = spec.goal_x
        self.goal_y = GROUND
        obj = os.path.join(BASE_DIR, "sprites", "object")
        self.background = Background(os.path.join(obj, spec.background),
                                     os.path.join(obj, spec.background_overlay))
        self.road = Road(os.path.join(obj, spec.road))
        self.lamp = Lamp()
        self.fence = Fence(os.path.join(obj, spec.fence))
        self.ground_spans = []
        self.furniture = []  # (종류, 그림 객체, 그림 중심 x)
        self.boss = (Boss(spec.boss_x, STAND_Y, spec.boss_left, spec.boss_right)
                     if spec.boss else None)
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
        box_half = Box(STAND_Y, self.spec.box_file).size() * 0.5
        bench_half = Bench(self.spec.bench_file).size() * 0.5
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
                lo = max(left + half, self.spec.furniture_min_x)
                hi = min(right - half, self.spec.furniture_max_x)
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
                self.furniture.append(("high", Box(STAND_Y, self.spec.box_file), cx))
        for _ in range(bench_count):
            cx = pick(bench_half)
            if cx is not None:
                self.furniture.append(("low", Bench(self.spec.bench_file), cx))

    def _place_pickups(self):
        """코인과 회복 아이템을 겹치지 않게 놓는다.

        - 회복 아이템: 윗면 몇 곳에 하나씩. 그 윗면에는 코인을 놓지 않는다.
        - 코인 줄: 일부 윗면에만 놓는다.
        - 구멍 몇 곳: 점프 포물선을 따라 코인을 놓는다.
        """
        spans = sorted(self.ground_spans)
        # 땅이 맞닿은 곳(폭 0)은 구멍이 아니므로 제외한다.
        gaps = [(a[1], b[0]) for a, b in zip(spans, spans[1:]) if b[0] - a[1] > 50]
        pit_count = self.spec.pit_arc_count
        for left, right in random.sample(gaps, min(pit_count, len(gaps))):
            self._place_pit_arc(left, right)

        surfaces = [p for p in self.platforms if p.one_way]
        heart_min_x = spans[self.spec.heart_min_segment][0]
        heart_pool = [p for p in surfaces if p.left >= heart_min_x]
        heart_surfaces = random.sample(heart_pool, min(self.spec.heart_count, len(heart_pool)))
        for plat in heart_surfaces:
            self.hearts.append(
                HeartPickup(plat.left + plat.width * 0.5, plat.top + PICKUP_LIFT,
                            random.random() * math.tau)
            )

        # 남은 코인 수만큼 윗면에 줄로 채운다(전체 COIN_TOTAL 개).
        budget = self.spec.coin_total - len(self.coins)
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
        spec = self.spec
        for left, right in spec.segments:
            self._add_ground(left, right)

        self.checkpoints = [Checkpoint(x, GROUND) for x in spec.checkpoints]

        # 벤치와 상자를 랜덤으로 배치하고, 그 윗면을 발판으로 만든다.
        self._place_furniture(spec.bench_count, spec.box_count)
        self._add_surfaces()

        for x1, x2, y in spec.coin_lines:
            self._coin_line(x1, x2, y)

        # 벤치/상자 윗면 위의 코인과 회복 아이템
        self._place_pickups()

        for x, left, right in spec.cats:
            self.enemies.append(
                Enemy("cat", x, STAND_Y, left, right, random.random() * math.tau)
            )
        for x, left, right in spec.ground_bears:
            self._add_bear(x, STAND_Y, left, right)
        for _ in range(spec.surface_bears):
            self._add_bear_on_surface()

        for x, y in spec.birds:
            self._add_bird(x, y)

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
        a = art()
        for coin in self.coins:
            coin.draw(a, camera_x, time, shake_x)

    def draw_hearts(self, camera_x, time, shake_x=0.0):
        a = art()
        for heart in self.hearts:
            heart.draw(a, camera_x, time, shake_x)

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


def hud_heart_image(filled):
    def paint():
        color = (255, 92, 128) if filled else (66, 70, 100)
        draw_heart_shape(32, 32, 26, color, filled=filled)

    return art().bake(("hud_heart", filled), 64, 64, paint)


class Game:
    # 테스트나 개발자 도구에서 오프닝을 건너뛰려면 True 로 바꾼다.
    skip_story = False

    def __init__(self):
        self.text = TextRenderer()
        self.stage = 1
        self.world = World(STAGES[self.stage])
        self.girl = Girl(160, STAND_Y)
        self.girl.limit_left = 24
        self.girl.limit_right = self.world.world_w - 24
        self.girl.dash_unlocked = self.world.spec.dash
        self.skill_bg = SkillBackground()
        self.hud = HUDOverlay()
        self.lobby = Lobby(WIDTH, HEIGHT, GROUND, STAND_Y)
        self.bgm = Bgm()
        self.sfx = Sfx()
        self.story = story.StoryPlayer(WIDTH, HEIGHT)
        self.story_images = {}

        self.state = "title"
        self.pending_skill_unlock = False
        self.skill_popup_time = 0.0
        self.intro_mode = "title"
        self.intro_time = 0.0
        self.time = 0.0
        self.play_time = 0.0
        self.camera = 0.0
        self.shake = 0.0
        self.shake_x = 0.0

        self.score = 0
        self.coin_count = 0
        self.kill_count = 0
        self.checkpoint = (160, STAND_Y)
        self.best_score = 0
        self.clear_bonus = 0

        self.particles = []
        self.slashes = []
        self.impacts = []
        self.bullets = []
        self.last_attack_id = 0
        self.dust_timer = 0.0
        self.fps = 0.0
        self.renderer_name = ""
        self.menu_index = 0
        self.options_index = 0
        # 개발자 메뉴(F11) 설정. 스테이지를 바꿔도 유지된다.
        self.dev_index = 0
        self.dev_prev_state = None
        self.dev_invincible = False
        self.dev_free_stage = False
        self.dev_no_cooldown = False

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
    def start(self, skip_story=False, skill_unlock=False):
        self.world = World(STAGES[self.stage])
        self.bgm.play(self.world.spec.bgm)
        self.girl = Girl(160, STAND_Y)
        self.girl.limit_left = 24
        self.girl.limit_right = self.world.world_w - 24
        self.girl.dash_unlocked = self.world.spec.dash
        self.girl.dev_invincible = self.dev_invincible
        self.girl.dev_no_cooldown = self.dev_no_cooldown
        self.girl.invuln = 0.0  # 시작할 때 깜빡이지 않도록
        self.bombs = BombField(self.world.ground_spans, sky_y=HEIGHT + 60,
                               ground_y=STAND_Y, enabled=self.world.spec.bombs)
        # 스킬 안내는 스테이지 2 오프닝(시나리오 → 타이틀)이 끝난 뒤에 띄운다.
        # 일반 클리어/개발자 이동 어느 경로로 들어와도 같게 표시한다.
        self.pending_skill_unlock = bool(
            skill_unlock or (self.stage == 2 and not skip_story
                             and not self.smoke and not self.skip_story))
        self.skill_popup_time = 0.0
        # 스테이지별 오프닝을 전투 전에 보여준다. smoke/개발자 이동은 생략.
        show_story = (self.stage in story.STORY_BY_STAGE
                      and not skip_story and not self.smoke
                      and not self.skip_story)
        if show_story:
            first = self.story.reset(self.stage)
            self.state = "cutscene"
            self._apply_story_effect(first)
        else:
            self.state = "play"
            if self.pending_skill_unlock:
                self.state = "skill_unlock"
                self.pending_skill_unlock = False
        self.play_time = 0.0
        self.intro_time = 0.0
        self.intro_mode = "title"
        self.camera = 0.0
        self.shake = 0.0
        self.score = 0
        self.coin_count = 0
        self.kill_count = 0
        self.checkpoint = (160, STAND_Y)
        self.clear_bonus = 0
        self.particles = []
        self.slashes = []
        self.impacts = []
        self.bullets = []
        self.last_attack_id = 0
        self.dust_timer = 0.0
        self.smoke_time = 0.0
        self.smoke_jump_t = 0.6
        self.smoke_attack_t = 0.4
        self.smoke_hit = False
        self.smoke_dead = False
        self.smoke_log = []
        pico2d.hide_cursor()

    def next_stage(self):
        """클리어 후 다음 스테이지로. 마지막 스테이지 다음은 1스테이지다."""
        was_dash = self.world.spec.dash
        self.stage = self.stage % len(STAGES) + 1
        # 스테이지 1을 클리어하고 오면 시나리오 뒤에 스킬 안내를 띄운다.
        unlock = not was_dash and STAGES[self.stage].dash
        self.start(skill_unlock=unlock)

    def close_skill_unlock(self):
        """해금 안내 팝업을 닫고 게임을 다시 시작한다."""
        if self.state == "skill_unlock":
            self.state = "play"
            self.girl.clear_keys()

    # ------------------------------------------------------------------
    # 스테이지 오프닝/엔딩 시나리오
    # ------------------------------------------------------------------
    def advance_story(self):
        """다음 대사(또는 빈 연출 턴)로 넘어간다."""
        if self.state != "cutscene":
            return
        step = self.story.advance()
        if self.story.finished:
            self.begin_stage_intro()
        elif step is not None:
            self._apply_story_effect(step)

    def story_input(self):
        """스페이스/엔터/클릭: 타이핑 중이면 전체 표시, 끝났으면 다음 턴."""
        if self.state != "cutscene":
            return
        if self.story.is_revealing:
            self.story.reveal_all()
        else:
            self.advance_story()

    def begin_ending_story(self):
        """스테이지 2 클리어 직후 엔딩 대사를 시작한다."""
        if self.state != "play":
            return
        first = self.story.reset("2_end")
        self.state = "cutscene"
        self._apply_story_effect(first)
        self.girl.clear_keys()

    def begin_stage_intro(self, mode=None):
        """마지막 대사 후 UI 페이드아웃 → 제목 또는 WARNING 연출로 간다."""
        if self.state != "cutscene":
            return
        self.story.finished = True
        self.state = "stage_intro"
        if mode is None:
            mode = "warning" if self.story.key == "2_end" else "title"
        self.intro_mode = mode
        self.intro_time = 0.0
        self.girl.clear_keys()
        pico2d.hide_cursor()

    def finish_cutscene(self):
        """ESC 건너뛰기 또는 타이틀 연출 종료 후 전투로 들어간다."""
        if self.state not in ("cutscene", "stage_intro"):
            return
        if self.state == "cutscene" and self.story.key == "2_end":
            # 엔딩 대사를 건너뛰어도 WARNING → 보스 스테이지 흐름은 유지한다.
            self.begin_stage_intro(mode="warning")
            return
        self.story.finished = True
        self.state = "play"
        if self.pending_skill_unlock:
            self.state = "skill_unlock"
            self.pending_skill_unlock = False
            self.skill_popup_time = 0.0
        self.girl.clear_keys()
        pico2d.hide_cursor()

    def enter_boss_stage(self):
        """WARNING 연출이 끝나면 보스가 있는 스테이지 3으로 진입한다."""
        self.stage = 3
        self.start(skip_story=True)
        self.state = "play"
        self.shake = 18.0
        self.sfx.play("bomb_sound.mp3")
        boss = self.world.boss
        if boss is not None:
            self.burst(boss.x, boss.y + boss.height * 0.5,
                       (255, 90, 80), 42, 460, 1.0, 7, gravity=120)

    def _apply_story_effect(self, step):
        """새 단계에 진입할 때 한 번만 실행되는 연출/효과음."""
        if step is None:
            return
        effect = step.get("effect")
        if effect == "quake":
            self.shake = max(self.shake, 20.0)
        elif effect == "explosion":
            self.sfx.play("bomb_sound.mp3")
            self.shake = max(self.shake, 16.0)
            self.burst(WIDTH * 0.5, HEIGHT * 0.58, (255, 170, 90),
                       36, 420, 1.0, 7)
        elif effect == "comm_beep":
            self.sfx.play("checkpoint_sound.mp3", volume=0.8)
        elif effect == "comm_end":
            self.sfx.play("checkpoint_sound.mp3", volume=0.5)
        elif effect == "weapon":
            self.sfx.play("skill_sound.mp3", volume=0.7)

    def toggle_dev_menu(self):
        """F11: 어느 화면에서든 개발자 메뉴를 열고 닫는다."""
        if self.state == "dev_menu":
            self.state = self.dev_prev_state or "play"
            if self.state in ("paused", "options"):
                pico2d.show_cursor()
            else:
                pico2d.hide_cursor()
            return
        self.dev_prev_state = self.state
        self.dev_index = 0
        self.girl.clear_keys()
        self.state = "dev_menu"
        pico2d.show_cursor()

    def toggle_dev_option(self):
        """개발자 메뉴에서 선택한 항목을 켜거나 끈다."""
        item = DEV_ITEMS[self.dev_index]
        if item == "invincible":
            self.dev_invincible = not self.dev_invincible
            self.girl.dev_invincible = self.dev_invincible
        elif item == "free_stage":
            self.dev_free_stage = not self.dev_free_stage
        else:
            self.dev_no_cooldown = not self.dev_no_cooldown
            self.girl.dev_no_cooldown = self.dev_no_cooldown
            if self.dev_no_cooldown:
                self.girl.dash_cooldown = 0.0

    def cycle_dev_stage(self, direction):
        """개발자 메뉴에서 스테이지를 바꾸고 해당 스테이지 시나리오부터 시작한다."""
        self.stage = (self.stage - 1 + direction) % len(STAGES) + 1
        self.dev_prev_state = None
        self.start()

    def toggle_pause(self):
        if self.state == "play":
            self.state = "paused"
            self.menu_index = 0
            self.girl.clear_keys()
            self.bgm.pause()
            pico2d.show_cursor()
        elif self.state == "paused":
            self.state = "play"
            self.bgm.resume()
            pico2d.hide_cursor()

    def open_options(self):
        """일시정지 메뉴의 옵션 화면으로 들어간다."""
        if self.state == "paused":
            self.state = "options"
            self.options_index = 0

    def close_options(self):
        """옵션 화면을 닫고 일시정지 메뉴로 돌아간다."""
        if self.state == "options":
            self.state = "paused"

    def adjust_option_volume(self, direction):
        """선택한 음량 슬라이드를 한 칸 움직인다."""
        if self.options_index == 0:
            audio.change_bgm_volume(VOLUME_STEP * direction)
        elif self.options_index == 1:
            audio.change_sfx_volume(VOLUME_STEP * direction)
            audio.apply_sfx_volumes()

    def toggle_option_mute(self):
        """전체 음소거를 켜거나 끈다."""
        audio.toggle_muted()

    # ------------------------------------------------------------------
    # 마우스 조작 (일시정지 / 옵션 / 개발자 메뉴)
    # ------------------------------------------------------------------
    @staticmethod
    def _mouse_pos(ev):
        """SDL 마우스 좌표를 게임 좌표(아래쪽이 +)로 바꾼다."""
        try:
            lx, ly = ctypes.c_int(), ctypes.c_int()
            pico2d.SDL_RenderWindowToLogical(
                pico2d.pico2d.renderer, int(ev.x), int(ev.y),
                ctypes.byref(lx), ctypes.byref(ly))
            return lx.value, HEIGHT - ly.value
        except Exception:
            return int(ev.x), HEIGHT - int(ev.y)

    def pause_item_rects(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        return [(cx - 170, cy + 30 - i * 56 - 22, 340, 44)
                for i in range(len(PAUSE_ITEMS))]

    def option_item_rects(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        ys = (cy + 55, cy - 5, cy - 65, cy - 125)
        return [(cx - 310, y - 18, 620, 36) for y in ys]

    def slider_bar_rect(self, item):
        cx, cy = WIDTH // 2, HEIGHT // 2
        y = cy + 55 if item == "bgm" else cy - 5
        return (cx - 80, y - 12, 270, 24)

    def dev_item_rects(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        return [(cx - 250, cy + 42 - i * 52 - 20, 500, 40)
                for i in range(len(DEV_ITEMS))]

    def dev_stage_button_rects(self):
        cx, cy = WIDTH // 2, HEIGHT // 2
        return ((cx - 170, cy - 122, 48, 34),
                (cx + 122, cy - 122, 48, 34))

    def handle_mouse_hover(self, ev):
        """메뉴 위에 마우스를 올리면 해당 항목을 선택한다."""
        x, y = self._mouse_pos(ev)
        if self.state == "paused":
            idx = hit_index(self.pause_item_rects(), x, y)
            if idx is not None:
                self.menu_index = idx
        elif self.state == "options":
            idx = hit_index(self.option_item_rects(), x, y)
            if idx is not None:
                self.options_index = idx
        elif self.state == "dev_menu":
            idx = hit_index(self.dev_item_rects(), x, y)
            if idx is not None:
                self.dev_index = idx

    def handle_mouse_click(self, ev):
        """메뉴 항목을 클릭한다. False 를 돌려주면 게임 종료 요청."""
        x, y = self._mouse_pos(ev)
        if self.state == "cutscene":
            self.story_input()
            return True
        if self.state == "stage_intro":
            if self.intro_mode == "warning":
                self.enter_boss_stage()
            else:
                self.finish_cutscene()
            return True
        if self.state == "paused":
            idx = hit_index(self.pause_item_rects(), x, y)
            if idx is None:
                return True
            self.menu_index = idx
            choice = PAUSE_ITEMS[idx]
            if choice == "resume":
                self.toggle_pause()
            elif choice == "options":
                self.open_options()
            else:
                return False
            return True

        if self.state == "options":
            idx = hit_index(self.option_item_rects(), x, y)
            if idx is None:
                return True
            self.options_index = idx
            item = OPTION_ITEMS[idx]
            if item in ("bgm", "sfx"):
                bar = self.slider_bar_rect(item)
                if in_rect(x, y, bar):
                    left, _, width, _ = bar
                    ratio = clamp((x - left) / float(width), 0.0, 1.0)
                    value = int(round(audio.MAX_VOLUME * ratio))
                    if item == "bgm":
                        audio.set_bgm_volume(value)
                    else:
                        audio.set_sfx_volume(value)
                        audio.apply_sfx_volumes()
            elif item == "mute":
                self.toggle_option_mute()
            else:
                self.close_options()
            return True

        if self.state == "dev_menu":
            idx = hit_index(self.dev_item_rects(), x, y)
            if idx is not None:
                self.dev_index = idx
                self.toggle_dev_option()
                return True
            if self.dev_free_stage:
                left_rect, right_rect = self.dev_stage_button_rects()
                if in_rect(x, y, left_rect):
                    self.cycle_dev_stage(-1)
                elif in_rect(x, y, right_rect):
                    self.cycle_dev_stage(1)
            return True

        if self.state == "play":
            self.girl.request_attack()
        return True

    # ------------------------------------------------------------------
    def update(self, dt):
        dt = min(dt, 0.05)
        self.time += dt
        self._update_motes(dt)
        self.skill_bg.update(dt, self.state == "play" and self.girl.state == "dash")

        if self.state == "title":
            if self.smoke and self.time > 0.7:
                self.start()
            return

        if self.state in ("paused", "options"):
            return

        # 해금 안내 팝업/개발자 메뉴가 떠 있는 동안에는 게임이 진행되지 않는다.
        if self.state == "skill_unlock":
            self.skill_popup_time += dt
            return
        if self.state == "dev_menu":
            return

        if self.state == "cutscene":
            self._update_cutscene(dt)
        elif self.state == "stage_intro":
            self._update_stage_intro(dt)
        elif self.state == "play":
            self._update_play(dt)
        else:
            self._update_effects(dt)

    def _update_cutscene(self, dt):
        step = self.story.update(dt)
        if step is not None:
            self._apply_story_effect(step)
        if self.story.finished:
            self.begin_stage_intro()
            return
        self._update_effects(dt)

    def _update_stage_intro(self, dt):
        self.intro_time += dt
        self._update_effects(dt)
        total = STORY_UI_FADE_TIME + STAGE_TITLE_FADE_IN + STAGE_TITLE_HOLD
        if self.intro_time >= total:
            if self.intro_mode == "warning":
                self.enter_boss_stage()
            else:
                self.finish_cutscene()

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

        self._prev_girl_x = self.girl.x
        self.girl.update(dt, self.world.platforms)
        if self.dev_no_cooldown:
            self.girl.dash_cooldown = 0.0

        # 카메라
        target = clamp(self.girl.focus_x() - WIDTH * 0.42, 0, self.world.world_w - WIDTH)
        self.camera += (target - self.camera) * min(1.0, dt * 7.0)

        # 착지/점프/달리기 먼지
        if self.girl.just_jumped:
            self.sfx.play("jump_sound.mp3")
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
        if self.world.boss is not None:
            self.world.boss.update(dt, self.girl.x)
        self._update_cats()
        self._update_bombs(dt)
        self._update_bullets(dt)

        self._check_attack()
        self._check_coins()
        self._check_hearts()
        self._check_checkpoints()
        self._check_goal()
        if self.state != "play":
            self._update_effects(dt)
            return
        self._check_enemy_contact()
        self._check_fall()

        self._update_effects(dt)

        if self.girl.state == "retire" and self.girl.retire_done:
            self.state = "gameover"
            self.best_score = max(self.best_score, self.score)

    def _fall_target(self, enemy):
        """쓰러진 적이 떨어질 y. 땅 위면 지면, 구덩이 위면 화면 아래 바깥."""
        on_ground = any(left <= enemy.x <= right for left, right in self.world.ground_spans)
        return STAND_Y if on_ground else -400

    def _update_cats(self):
        """고양이는 처음 나타날 때부터 5초마다 총을 쏜다.

        발사 시각은 화면과 상관없이 5초 간격으로 흘러간다. 화면 밖에서 발사 시각이 와도 총알은 나간다.
        공격 모션은 화면에 나타나는 순간과 발사 직전에 재생한다.
        """
        now = self.time
        for enemy in self.world.enemies:
            if enemy.kind != "cat" or not enemy.alive:
                continue
            visible = -80 < enemy.x - self.camera < WIDTH + 80
            if enemy.next_shot is None and visible:
                enemy.next_shot = now + CAT_FIRE_TIME
            if visible and not enemy.is_attacking():
                pre_roll = enemy.next_shot is not None and now >= enemy.next_shot - CAT_FIRE_TIME
                if pre_roll or (not enemy.was_visible and enemy.next_shot is not None):
                    enemy.begin_attack()
            enemy.was_visible = visible
            if enemy.is_attacking():
                # 공격하는 동안에는 캐릭터 쪽을 바라본다.
                enemy.facing = 1 if self.girl.focus_x() >= enemy.x else -1
            if enemy.next_shot is not None and now >= enemy.next_shot:
                mx, my = muzzle(enemy.x, enemy.y, enemy.facing)
                self.bullets.append(Bullet(mx, my, enemy.facing))
                self.sfx.play("gunfire_sound.mp3")
                enemy.next_shot += CAT_SHOT_INTERVAL

    def _update_bombs(self, dt):
        for bomb in self.bombs.update(dt, self.camera):
            self.sfx.play("bomb_sound.mp3")
            left, bottom, w, h = bomb.hit_rect()
            if overlaps(*self.girl.rect(), left, bottom, w, h):
                if self.girl.take_hit(bomb.x):
                    self.sfx.play("female_deathsound.mp3")
                    self.shake = max(self.shake, 11.0)
            self.burst(bomb.x, STAND_Y + 20, (255, 170, 90), 22, 320, 0.6, 5)
            self.shake = max(self.shake, 6.0)

    def _update_bullets(self, dt):
        girl_rect = self.girl.rect()
        for bullet in self.bullets:
            bullet.update(dt)
            if bullet.alive and overlaps(*girl_rect, *bullet.rect()):
                bullet.alive = False
                if self.girl.take_hit(bullet.x):
                    self.sfx.play("female_deathsound.mp3")
                    self.shake = max(self.shake, 11.0)
        self.bullets = [b for b in self.bullets if b.alive]

    def _check_attack(self):
        hitbox = self.girl.attack_hitbox()
        if self.girl.attack_id != self.last_attack_id:
            self.last_attack_id = self.girl.attack_id
            self.slashes.append(
                Slash(self.girl, self.girl.facing)
            )
            self.sfx.play("punch_sound.mp3", 0.5)
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
                enemy.kill(self._fall_target(enemy))
                self.sfx.play(death_sound(enemy))
                self.kill_count += 1
                enemy.last_attack = self.girl.attack_id
                self.score += 100
                self.shake = max(self.shake, 5.0)
                color = (160, 120, 255) if enemy.kind == "bird" else (110, 75, 190)
                self.burst(enemy.x, enemy.y + enemy.height * 0.5, color,
                           14, 300, 0.55, 4)

        boss = self.world.boss
        if (boss is not None and boss.alive
                and boss.last_attack != self.girl.attack_id
                and overlaps(*hitbox, *boss.rect())):
            if boss.hurt():
                self.score += 100
                self.shake = max(self.shake, 6.0)
                self.burst(boss.x, boss.y + boss.height * 0.55,
                           (255, 190, 110), 18, 340, 0.6, 5)
            boss.last_attack = self.girl.attack_id
            if boss.defeated:
                self._boss_defeated()

    def _boss_defeated(self):
        """보스를 쓰러뜨리면 3스테이지는 즉시 클리어된다."""
        if self.state != "play":
            return
        self.state = "clear"
        self.clear_bonus = int(max(0, self.world.spec.time_bonus - self.play_time * 25))
        self.score += self.clear_bonus + 500
        self.best_score = max(self.best_score, self.score)
        self.kill_count += 1
        self.shake = 12.0
        self.sfx.play("bear_deathsound.mp3")
        self.burst(self.world.boss.x, self.world.boss.y + 140,
                   (255, 200, 120), 50, 440, 1.0, 6, gravity=120)

    def _check_coins(self):
        for coin in self.world.coins:
            if coin.taken:
                continue
            if overlaps(*self.girl.rect(),
                        coin.x - 16, coin.y - 16, 32, 32):
                coin.taken = True
                self.coin_count += 1
                self.sfx.play("coin_sound.mp3")
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
                self.sfx.play("heal_sound.mp3")
                if self.girl.hp < self.girl.MAX_HP:
                    self.girl.heal(1)
                else:
                    self.score += 50
                self.burst(heart.x, heart.y, (255, 110, 150),
                           14, 240, 0.6, 4, gravity=300)

    def _check_checkpoints(self):
        # 대쉬로 한 프레임에 많이 움직여도 놓치지 않도록, 이전 위치부터 현재 위치까지 확인한다.
        lo = min(self._prev_girl_x, self.girl.x)
        hi = max(self._prev_girl_x, self.girl.x)
        for cp in self.world.checkpoints:
            if cp.active:
                continue
            if lo - 46 <= cp.x <= hi + 46 and self.girl.y <= cp.y + CHECKPOINT_REACH_Y:
                cp.active = True
                self.sfx.play("checkpoint_sound.mp3")
                self.checkpoint = (cp.x, cp.y + 2)
                self.girl.heal(1)
                self.burst(cp.x, cp.y + 110, (120, 250, 220),
                           22, 280, 0.7, 4, gravity=200)

    def _check_goal(self):
        if self.state != "play":
            return
        # 보스 스테이지에서는 보스를 쓰러뜨려야 문이 열린다(쓰러뜨리면 즉시 클리어).
        if self.world.boss is not None and not self.world.boss.defeated:
            return
        if abs(self.girl.x - self.world.goal_x) < 46:
            self.clear_bonus = int(max(0, self.world.spec.time_bonus - self.play_time * 25))
            self.score += self.clear_bonus
            self.best_score = max(self.best_score, self.score)
            self.shake = 8.0
            self.burst(self.world.goal_x, GROUND + 100,
                       (140, 255, 240), 40, 420, 0.9, 5, gravity=120)
            if self.stage == 2:
                self.begin_ending_story()
            else:
                self.state = "clear"

    def _check_enemy_contact(self):
        gx, gy, gw, gh = self.girl.rect()
        boss = self.world.boss
        if boss is not None and boss.alive:
            bx, by, bw, bh = boss.rect()
            if overlaps(gx, gy, gw, gh, bx, by, bw, bh):
                stomp = (
                    self.girl.vy < -80.0
                    and self.girl.prev_y >= by + bh - 16
                    and self.girl.y <= by + bh + 34
                )
                if self.girl.dash_timer > 0.0 or stomp:
                    if boss.hurt():
                        self.sfx.play("punch_sound.mp3", 0.4)
                        self.shake = max(self.shake, 6.0)
                        self.burst(boss.x, boss.y + boss.height * 0.55,
                                   (255, 190, 110), 16, 320, 0.6, 5)
                    if stomp:
                        self.girl.bounce(700.0)
                    if boss.defeated:
                        self._boss_defeated()
                else:
                    boss.touch()
                    if self.girl.take_hit(boss.x):
                        self.sfx.play("female_deathsound.mp3")
                        self.shake = max(self.shake, 11.0)
                        self.burst(self.girl.x, self.girl.y + 100,
                                   (255, 120, 140), 16, 320, 0.6, 4)
                        if self.girl.hp <= 0:
                            self.shake = 18.0
                            self.best_score = max(self.best_score, self.score)
        for enemy in self.world.enemies:
            if not enemy.alive:
                continue
            ex, ey, ew, eh = enemy.rect()
            if not overlaps(gx, gy, gw, gh, ex, ey, ew, eh):
                continue
            if self.girl.dash_timer > 0.0:
                # 대쉬 중에 닿은 적은 바로 사망한다.
                enemy.kill(self._fall_target(enemy))
                self.sfx.play(death_sound(enemy))
                self.kill_count += 1
                self.sfx.play("punch_sound.mp3", 0.4)
                self.impacts.append(PunchImpact(
                    (self.girl.focus_x() + enemy.x) * 0.5,
                    enemy.y + enemy.height * 0.5, self.girl.facing))
                self.score += 100
                self.shake = max(self.shake, 5.0)
                color = (160, 120, 255) if enemy.kind == "bird" else (110, 75, 190)
                self.burst(enemy.x, enemy.y + enemy.height * 0.5, color,
                           14, 300, 0.55, 4)
                continue
            stomp = (
                self.girl.vy < -80.0
                and self.girl.prev_y >= ey + eh - 16
                and self.girl.y <= ey + eh + 34
            )
            if stomp:
                enemy.kill(self._fall_target(enemy))
                self.sfx.play(death_sound(enemy))
                self.kill_count += 1
                self.girl.bounce(700.0)
                self.score += 150
                self.shake = max(self.shake, 6.0)
                color = (160, 120, 255) if enemy.kind == "bird" else (110, 75, 190)
                self.burst(enemy.x, enemy.y + enemy.height * 0.5, color,
                           16, 300, 0.55, 4)
            else:
                enemy.touch()
                if self.girl.take_hit(enemy.x):
                    self.sfx.play("female_deathsound.mp3")
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
        if self.dev_invincible:
            # 무적 모드에서는 구멍에 떨어져도 죽지 않고 체크포인트로 돌아간다.
            self.girl.respawn(*self.checkpoint)
            self.shake = 10.0
            return
        self.sfx.play("falling_sound.mp3")
        self.sfx.play("female_deathsound.mp3")
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
        for impact in self.impacts:
            impact.update(dt)
        self.impacts = [i for i in self.impacts if i.alive]
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

        if (self.state in ("cutscene", "stage_intro")
                or (self.state == "dev_menu"
                    and self.dev_prev_state in ("cutscene", "stage_intro"))):
            shown = self.state if self.state != "dev_menu" else self.dev_prev_state
            if shown == "cutscene":
                self._draw_cutscene()
            else:
                self._draw_stage_intro()
            if self.state == "dev_menu":
                self._draw_dev_menu()
            return

        self.world.draw_background(self.camera, self.time, self.shake_x)

        if self.state == "title" or (self.state == "dev_menu"
                                     and self.dev_prev_state == "title"):
            self.lobby.draw(self, art())
            if self.state == "dev_menu":
                self._draw_dev_menu()
            return

        self._draw_world()
        self.world.draw_motes(self.motes)
        self._draw_hud()

        if self.state == "dev_menu":
            self._draw_dev_menu()
        elif self.state == "options":
            self._draw_options()
        elif self.state == "paused":
            self._draw_pause()
        elif self.state == "skill_unlock":
            self._draw_skill_unlock()
        elif self.state == "clear":
            self._draw_clear()
        elif self.state == "gameover":
            self._draw_gameover()

    def _story_portrait(self, speaker):
        path = story.portrait_path(speaker)
        if not path:
            return None
        image = self.story_images.get(path)
        if image is None:
            image = pico2d.load_image(os.path.join(BASE_DIR, path))
            self.story_images[path] = image
        return image

    def _wrap_story_text(self, text, size=26, max_width=None):
        """긴 한국어 대사를 화면 폭에 맞춰 줄바꿈한다."""
        if max_width is None:
            max_width = WIDTH - 240
        lines = []
        current = ""
        for ch in text:
            candidate = current + ch
            if current and self.text.measure(size, candidate) > max_width:
                lines.append(current.rstrip())
                current = ch.lstrip()
            else:
                current = candidate
        if current.strip():
            lines.append(current.rstrip())
        return lines or [""]

    def _draw_cutscene(self):
        a = art()
        s = self.story
        step = s.current()
        ox = self.shake_x + s.portrait_sway()

        # 배경은 그대로 게임플레이 화면을 어둡게 보여준다.
        self.world.draw_background(self.camera, self.time, self.shake_x)
        self._draw_world()
        self.world.draw_motes(self.motes)
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 0, 0, 0, 118, filled=True)

        # 연기/폭발 파티클은 UI 아래에 깔아야 한다.
        if s.smoke_scene:
            smoke = a.disc((150, 152, 160), glow=True)
            for px, py, radius, alpha, _ in s.smoke_puffs:
                a.blit(smoke, px + ox * 0.4, py, radius * 2, radius * 2,
                       int(alpha * 255 * 0.55))

        # PNG 안에 이미 이름/네모박스가 들어 있으므로 초상화만 얹는다.
        portrait = self._story_portrait(s.speaker)
        if portrait is not None:
            a.blit(portrait, WIDTH * 0.5 + ox, HEIGHT * 0.5, WIDTH, HEIGHT)

        # 예시 이미지에서 측정한 위치에 대사만 출력한다.
        if step is not None and step["kind"] == "line" and s.visible_text:
            y = STORY_TEXT_Y
            for line in self._wrap_story_text(
                    s.visible_text, STORY_TEXT_SIZE, STORY_TEXT_WIDTH)[:2]:
                self.text.draw(STORY_TEXT_SIZE, STORY_TEXT_X, y, line,
                               (244, 240, 232), shadow=(6, 6, 16))
                y -= STORY_LINE_GAP

        if s.flash > 0.0:
            pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT,
                                  255, 210, 150, int(190 * s.flash),
                                  filled=True)
        fade = s.fade_alpha()
        if fade > 0:
            pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 0, 0, 0, fade,
                                  filled=True)

    def _story_ui_alpha(self):
        """대화 UI 페이드아웃 알파(0~255)."""
        if self.state == "cutscene":
            return 255
        if self.state != "stage_intro":
            return 0
        t = clamp(self.intro_time / STORY_UI_FADE_TIME, 0.0, 1.0)
        return int(255 * (1.0 - t))

    def _stage_title_alpha(self):
        """UI 가 다 사라진 뒤 나타나는 제목의 표시 비율(0~1)."""
        if self.state != "stage_intro":
            return 0.0
        t = (self.intro_time - STORY_UI_FADE_TIME) / STAGE_TITLE_FADE_IN
        return clamp(t, 0.0, 1.0)

    def _draw_stage_intro(self):
        a = art()
        # 시나리오와 같은 어두운 게임플레이 화면 위에 연출을 겹친다.
        self.world.draw_background(self.camera, self.time, self.shake_x)
        self._draw_world()
        self.world.draw_motes(self.motes)
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 0, 0, 0, 118, filled=True)

        # 이름표/대사창이 들어 있는 PNG 자체를 서서히 투명하게 만든다.
        ui_alpha = self._story_ui_alpha()
        if ui_alpha > 0:
            portrait = self._story_portrait(self.story.speaker)
            if portrait is not None:
                a.blit(portrait, WIDTH * 0.5 + self.shake_x, HEIGHT * 0.5,
                       WIDTH, HEIGHT, ui_alpha)

        # UI 가 완전히 사라진 뒤 중앙에 제목(또는 WARNING)을 띄운다.
        title_alpha = self._stage_title_alpha()
        if title_alpha > 0.0:
            cx, cy = WIDTH // 2, HEIGHT // 2
            if self.intro_mode == "warning":
                pulse = 0.66 + 0.34 * abs(math.sin(self.intro_time * 9.0))
                alert = tuple(int(c * title_alpha * pulse)
                              for c in (255, 74, 74))
                self.text.draw(WARNING_SIZE, cx, cy, WARNING_TEXT,
                               alert, "center", shadow=None)
            else:
                big = tuple(int(c * title_alpha) for c in (255, 222, 150))
                small = tuple(int(c * title_alpha) for c in (232, 238, 250))
                title, subtitle = story.stage_title(self.stage)
                if title:
                    self.text.draw(STAGE_TITLE_LARGE_SIZE, cx, cy + 34, title,
                                   big, "center", shadow=None)
                if subtitle:
                    self.text.draw(STAGE_TITLE_SMALL_SIZE, cx, cy - 42, subtitle,
                                   small, "center", shadow=None)

    def _draw_world(self):
        cam = self.camera
        shake = self.shake_x

        self.world.draw_fence(cam, shake)
        self.world.draw_platforms(cam, shake)
        self.world.draw_checkpoints(cam, self.time, shake)
        self.world.draw_goal(cam, self.time, shake)
        self.world.draw_coins(cam, self.time, shake)
        self.world.draw_hearts(cam, self.time, shake)

        self.bombs.draw_warnings(art(), cam, shake)
        for enemy in self.world.enemies:
            enemy.draw(cam, self.time, shake)
        self.bombs.draw(cam, shake)
        if self.world.boss is not None:
            self.world.boss.draw(art(), cam, shake)

        # 스킬 배경: 다른 레이어 위, 캐릭터 바로 아래
        self.skill_bg.draw(art(), WIDTH, HEIGHT)

        self.girl.draw(cam, shake, self.time)

        self.bombs.draw_blasts(cam, shake)

        for particle in self.particles:
            particle.draw(cam, shake)
        for slash in self.slashes:
            slash.draw(cam, shake)
        for impact in self.impacts:
            impact.draw(cam, shake)
        for bullet in self.bullets:
            bullet.draw(cam, shake)

    def _draw_hud(self):
        a = art()
        cooldown = self.girl.dash_cooldown / Girl.DASH_COOLDOWN
        self.hud.draw(a, WIDTH, HEIGHT, self.girl.hp, cooldown,
                      dash_locked=not self.girl.dash_unlocked)
        # 스킬 쿨타임: 아이콘 한가운데에 남은 초를 표시하고, 0이 되면 사라진다.
        if self.girl.dash_cooldown > 0.0:
            icon_x, icon_y = skill_icon_center(WIDTH, HEIGHT)
            # 폰트 그림은 아래쪽 여백(디센더) 때문에 숫자 잉크가 조금 위로 뜬다.
            self.text.draw(24, icon_x, icon_y - 3,
                           "%d" % math.ceil(self.girl.dash_cooldown),
                           (255, 236, 190), "center")
        # 점수
        self.text.draw(24, 30, HEIGHT - 52,
                       "SCORE %06d" % self.score, (230, 236, 250))
        # 코인 (점수 바로 아래)
        a.blit(coin_image(), 44, HEIGHT - 94, 28, 28)
        self.text.draw(24, 66, HEIGHT - 94,
                       "x %02d" % self.coin_count, (240, 220, 150))
        a.blit(kill_icon(), 44, HEIGHT - 130, 44, 36)
        self.text.draw(24, 66, HEIGHT - 130,
                       "x %02d" % self.kill_count, (240, 200, 200))
        minutes = int(self.play_time) // 60
        seconds = int(self.play_time) % 60
        self.text.draw(18, WIDTH * 0.5, HEIGHT - 52,
                       "STAGE %d" % self.stage, (200, 210, 235), align="center")
        self.text.draw(20, WIDTH * 0.5, HEIGHT - 80,
                       "TIME %02d:%02d" % (minutes, seconds),
                       (170, 190, 220), align="center")

        # 진행도
        bar_left, bar_right, bar_y = 430, 850, HEIGHT - 26
        pico2d.draw_line(bar_left, bar_y, bar_right, bar_y, 70, 78, 118)
        progress = clamp(self.girl.x / self.world.goal_x, 0.0, 1.0)
        px = bar_left + (bar_right - bar_left) * progress
        pico2d.draw_rectangle(bar_left, bar_y - 1, px, bar_y + 1,
                              60, 220, 190, filled=True)
        a.blit(a.disc((150, 255, 235)), px, bar_y, 10, 10)

        self._draw_fps(WIDTH - 24, HEIGHT - 26, align="right")
        if self.world.boss is not None:
            self._draw_boss_hp()

    def _draw_boss_hp(self):
        """보스 스테이지에서는 화면 위쪽에 보스 체력을 표시한다."""
        boss = self.world.boss
        cx = WIDTH * 0.5
        y = HEIGHT - 116
        self.text.draw(20, cx, y + 22, "보스", (255, 210, 170), "center")
        left, right = cx - 200, cx + 200
        pico2d.draw_rectangle(left, y - 5, right, y + 5, 40, 24, 34, 220,
                              filled=True)
        pico2d.draw_rectangle(left, y - 5, right, y + 5,
                              240, 180, 150, 180)
        ratio = boss.hp / boss.max_hp
        if ratio > 0.0:
            pico2d.draw_rectangle(left, y - 4, left + 400 * ratio, y + 4,
                                  255, 120, 90, 240, filled=True)
        self.text.draw(16, cx, y - 28,
                       "%d / %d" % (boss.hp, boss.max_hp),
                       (240, 200, 190), "center", shadow=None)

    def _draw_fps(self, x, y, align="left"):
        if self.fps <= 0.0:
            return
        color = (140, 230, 190) if self.fps >= 50.0 else (255, 190, 120)
        self.text.draw(16, x, y, "FPS %d" % round(self.fps), color,
                       align=align, shadow=None)

    def _draw_pause(self):
        """일시정지 팝업 메뉴."""
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 150,
                              filled=True)
        cx, cy = WIDTH // 2, HEIGHT // 2
        pico2d.draw_rectangle(cx - 210, cy - 170, cx + 210, cy + 170,
                              20, 26, 52, 235, filled=True)
        pico2d.draw_rectangle(cx - 210, cy - 170, cx + 210, cy + 170,
                              120, 220, 210, 200)
        self.text.draw(44, cx, cy + 110, "PAUSED", (235, 240, 255), "center")
        labels = {"resume": "계속하기", "options": "옵션", "quit": "게임 종료"}
        for i, item in enumerate(PAUSE_ITEMS):
            selected = i == self.menu_index
            color = (255, 236, 190) if selected else (150, 160, 190)
            prefix = "> " if selected else "  "
            self.text.draw(28, cx, cy + 30 - i * 56, prefix + labels[item],
                           color, "center")
        self.text.draw(16, cx, cy - 145,
                       "UP / DOWN 선택   ENTER/클릭 확인   ESC 닫기",
                       (120, 136, 172), "center", shadow=None)

    def _draw_options(self):
        """일시정지 메뉴의 옵션: 음량 슬라이드와 전체 음소거."""
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 180,
                              filled=True)
        cx, cy = WIDTH // 2, HEIGHT // 2
        pico2d.draw_rectangle(cx - 350, cy - 195, cx + 350, cy + 195,
                              18, 22, 44, 240, filled=True)
        pico2d.draw_rectangle(cx - 350, cy - 195, cx + 350, cy + 195,
                              120, 200, 240, 210)
        self.text.draw(40, cx, cy + 145, "옵션", (150, 230, 255), "center")

        bar_left, bar_right = cx - 80, cx + 190
        bar_width = bar_right - bar_left
        rows = (("bgm", "배경음악", cy + 55),
                ("sfx", "효과음", cy - 5))
        for i, (item, label, y) in enumerate(rows):
            selected = i == self.options_index
            color = (255, 236, 190) if selected else (150, 160, 190)
            marker = "> " if selected else "  "
            self.text.draw(24, cx - 300, y - 8, marker + label, color, "left")
            pico2d.draw_rectangle(bar_left, y - 8, bar_right, y + 8,
                                  30, 36, 58, 230, filled=True)
            value = (audio.bgm_percent() if item == "bgm"
                     else audio.sfx_percent())
            knob = bar_left + int(bar_width * value / 100.0)
            if knob > bar_left:
                fill_color = ((90, 100, 120, 220) if audio.is_muted()
                              else (90, 200, 240, 240))
                pico2d.draw_rectangle(bar_left, y - 6, knob, y + 6,
                                      *fill_color, filled=True)
            pico2d.draw_rectangle(bar_left, y - 8, bar_right, y + 8,
                                  120, 160, 210, 180)
            pico2d.draw_rectangle(knob - 4, y - 13, knob + 4, y + 13,
                                  235, 245, 255, 255, filled=True)
            self.text.draw(20, cx + 215, y - 8, "%d%%" % value,
                           (210, 225, 245), "left", shadow=None)

        y = cy - 65
        selected = self.options_index == 2
        color = (255, 236, 190) if selected else (150, 160, 190)
        marker = "> " if selected else "  "
        state = "ON" if audio.is_muted() else "OFF"
        state_color = (255, 130, 140) if audio.is_muted() else (140, 230, 190)
        self.text.draw(24, cx - 300, y - 8, marker + "전체 음소거", color,
                       "left")
        self.text.draw(24, cx - 80, y - 8, state, state_color, "left")

        y = cy - 125
        selected = self.options_index == 3
        color = (255, 236, 190) if selected else (150, 160, 190)
        marker = "> " if selected else "  "
        self.text.draw(24, cx - 300, y - 8, marker + "뒤로", color, "left")
        self.text.draw(16, cx, cy - 170,
                       "↑/↓ 선택   ←/→ 또는 클릭으로 음량 조절   ENTER 토글   ESC 뒤로",
                       (120, 136, 172), "center", shadow=None)

    def _draw_dev_menu(self):
        """개발자 메뉴(F11): 무적 / 자유로운 스테이지 이동 / 스킬 쿨타임 0초."""
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 180,
                              filled=True)
        cx, cy = WIDTH // 2, HEIGHT // 2
        pico2d.draw_rectangle(cx - 310, cy - 150, cx + 310, cy + 150,
                              18, 22, 44, 240, filled=True)
        pico2d.draw_rectangle(cx - 310, cy - 150, cx + 310, cy + 150,
                              120, 200, 240, 210)
        self.text.draw(38, cx, cy + 106, "DEV MENU", (150, 230, 255),
                       "center")
        labels = {
            "invincible": "무적",
            "free_stage": "자유롭게 스테이지 이동",
            "no_cooldown": "스킬 쿨타임 0초",
        }
        flags = {
            "invincible": self.dev_invincible,
            "free_stage": self.dev_free_stage,
            "no_cooldown": self.dev_no_cooldown,
        }
        for i, item in enumerate(DEV_ITEMS):
            selected = i == self.dev_index
            color = (255, 236, 190) if selected else (150, 160, 190)
            marker = "> " if selected else "  "
            state = "ON" if flags[item] else "OFF"
            self.text.draw(26, cx, cy + 42 - i * 52,
                           "%s%s : %s" % (marker, labels[item], state),
                           color, "center")

        for rect, label in zip(self.dev_stage_button_rects(), ("◀", "▶")):
            left, bottom, width, height = rect
            enabled = self.dev_free_stage
            fill = (55, 95, 150, 230) if enabled else (35, 40, 55, 170)
            text_color = ((220, 235, 255) if enabled else (100, 110, 130))
            pico2d.draw_rectangle(left, bottom, left + width, bottom + height,
                                  *fill, filled=True)
            pico2d.draw_rectangle(left, bottom, left + width, bottom + height,
                                  120, 180, 230, 190)
            self.text.draw(22, left + width // 2, bottom + 8, label,
                           text_color, "center", shadow=None)
        self.text.draw(16, cx, cy - 142,
                       "↑/↓ 선택   ENTER/클릭 토글   ←/→ 또는 버튼 스테이지 이동   F11 닫기",
                       (130, 150, 190), "center", shadow=None)

    def _draw_skill_unlock(self):
        """대쉬 스킬 해금 안내 팝업. 스페이스바로 닫는다."""
        pico2d.draw_rectangle(0, 0, WIDTH, HEIGHT, 8, 10, 24, 170,
                              filled=True)
        cx, cy = WIDTH // 2, HEIGHT // 2
        pico2d.draw_rectangle(cx - 300, cy - 130, cx + 300, cy + 130,
                              20, 26, 52, 235, filled=True)
        pico2d.draw_rectangle(cx - 300, cy - 130, cx + 300, cy + 130,
                              120, 220, 210, 200)
        self.text.draw(40, cx, cy + 62, "스킬이 해금되었습니다!",
                       (130, 250, 225), "center")
        self.text.draw(28, cx, cy + 2, "스킬 : 싼데안비슷한 (Q)",
                       (255, 236, 190), "center")
        self.text.draw(18, cx, cy - 96, "SPACE 키를 누르면 닫힙니다",
                       (120, 136, 172), "center", shadow=None)

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
                       "R 키를 눌러 다음 스테이지", (170, 200, 230), "center")

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


def toggle_fullscreen():
    """F12: 창 모드와 전체 화면을 바꾼다. 전체 화면에서도 게임 화면 비율을 유지한다."""
    window = pico2d.pico2d.window
    flags = sdl2.SDL_GetWindowFlags(window)
    if flags & sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP:
        sdl2.SDL_SetWindowFullscreen(window, 0)
    else:
        sdl2.SDL_SetWindowFullscreen(window, sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP)
    # 게임은 WIDTH x HEIGHT 기준으로 그리므로, 창이 커져도 그 크기에 맞춰 늘린다.
    art().logical = (WIDTH, HEIGHT)
    sdl2.SDL_RenderSetLogicalSize(pico2d.pico2d.renderer, WIDTH, HEIGHT)
    # 화면 모드가 바뀌면 구워 둔 그림이 지워지므로 다시 굽는다.
    art().repaint_all()


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
                if ev.key == sdl2.SDLK_F11:
                    game.toggle_dev_menu()
                elif ev.key == sdl2.SDLK_F12:
                    toggle_fullscreen()
                elif game.state == "dev_menu":
                    if ev.key in (sdl2.SDLK_ESCAPE, sdl2.SDLK_F11):
                        game.toggle_dev_menu()
                    elif ev.key in (sdl2.SDLK_UP, sdl2.SDLK_DOWN):
                        step = -1 if ev.key == sdl2.SDLK_UP else 1
                        game.dev_index = (game.dev_index + step) % len(DEV_ITEMS)
                    elif ev.key in (sdl2.SDLK_RETURN, sdl2.SDLK_SPACE):
                        game.toggle_dev_option()
                    elif (game.dev_free_stage
                          and ev.key in (sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT)):
                        step = -1 if ev.key == sdl2.SDLK_LEFT else 1
                        game.cycle_dev_stage(step)
                elif game.state == "cutscene":
                    # Space/Enter: 타이핑 중엔 전체 표시, 다 나왔으면 다음 턴.
                    if ev.key in (sdl2.SDLK_SPACE, sdl2.SDLK_RETURN):
                        game.story_input()
                    elif ev.key == sdl2.SDLK_ESCAPE:
                        game.finish_cutscene()
                elif game.state == "stage_intro":
                    if ev.key in (sdl2.SDLK_SPACE, sdl2.SDLK_RETURN,
                                  sdl2.SDLK_ESCAPE):
                        if game.intro_mode == "warning":
                            game.enter_boss_stage()
                        else:
                            game.finish_cutscene()
                elif game.state in ("clear", "gameover"):
                    # 스테이지 종료 화면에서는 R 키만 받는다.
                    if ev.key == sdl2.SDLK_r:
                        if game.state == "clear":
                            game.next_stage()
                        else:
                            game.start()
                elif game.state == "options":
                    if ev.key in (sdl2.SDLK_ESCAPE, sdl2.SDLK_p):
                        game.close_options()
                    elif ev.key == sdl2.SDLK_UP:
                        game.options_index = ((game.options_index - 1)
                                              % len(OPTION_ITEMS))
                    elif ev.key == sdl2.SDLK_DOWN:
                        game.options_index = ((game.options_index + 1)
                                              % len(OPTION_ITEMS))
                    elif (ev.key in (sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT)
                          and game.options_index in (0, 1)):
                        step = -1 if ev.key == sdl2.SDLK_LEFT else 1
                        game.adjust_option_volume(step)
                    elif ev.key in (sdl2.SDLK_RETURN, sdl2.SDLK_SPACE):
                        if game.options_index == 2:
                            game.toggle_option_mute()
                        elif game.options_index == 3:
                            game.close_options()
                elif game.state == "paused":
                    if ev.key in (sdl2.SDLK_ESCAPE, sdl2.SDLK_p):
                        game.toggle_pause()
                    elif ev.key == sdl2.SDLK_UP:
                        game.menu_index = (game.menu_index - 1) % len(PAUSE_ITEMS)
                    elif ev.key == sdl2.SDLK_DOWN:
                        game.menu_index = (game.menu_index + 1) % len(PAUSE_ITEMS)
                    elif ev.key in (sdl2.SDLK_RETURN, sdl2.SDLK_SPACE):
                        choice = PAUSE_ITEMS[game.menu_index]
                        if choice == "resume":
                            game.toggle_pause()
                        elif choice == "options":
                            game.open_options()
                        else:
                            running = False
                elif game.state == "skill_unlock":
                    # 해금 안내 팝업은 스페이스바로만 닫는다.
                    # 연속 입력을 막아 팝업이 스쳐 지나가지 않게 한다.
                    if (ev.key == sdl2.SDLK_SPACE
                            and game.skill_popup_time >= SKILL_POPUP_INPUT_DELAY):
                        game.close_skill_unlock()
                elif ev.key == sdl2.SDLK_ESCAPE:
                    if game.state == "play":
                        game.toggle_pause()
                    else:
                        running = False
                elif ev.key == sdl2.SDLK_p and game.state == "play":
                    game.toggle_pause()
                elif game.state == "play":
                    if game.girl.handle_event(ev):
                        game.sfx.play("skill_sound.mp3")
                elif game.state == "title":
                    if ev.key in (sdl2.SDLK_SPACE, sdl2.SDLK_RETURN,
                                  sdl2.SDLK_r):
                        game.start()
            elif ev.type == sdl2.SDL_KEYUP:
                if game.state == "play":
                    game.girl.handle_event(ev)
            elif ev.type == sdl2.SDL_MOUSEMOTION:
                game.handle_mouse_hover(ev)
            elif (ev.type == sdl2.SDL_MOUSEBUTTONDOWN
                  and ev.button == sdl2.SDL_BUTTON_LEFT):
                if not game.handle_mouse_click(ev):
                    running = False

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

    game.bgm.close()
    pico2d.close_canvas()


if __name__ == "__main__":
    main()
