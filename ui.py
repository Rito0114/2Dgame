"""화면 UI 오버레이: UI 배경, 목숨(hp), 스킬 쿨타임.

- UI_background.png: UI 배경. 왼쪽 아래에 그려진다.
- hp_N.png: 잃은 목숨의 수만큼 켠다.
  목숨이 전부 있으면 아무것도 켜지지 않고, 하나 잃으면 hp_1, 둘 잃으면 hp_1 과 hp_2 를 켠다.
  회복 아이템으로 목숨이 하나 늘면 가장 마지막에 켜진 hp 그림이 꺼진다.
- skill_time.png: 스킬을 쓰면 나타나고, 쿨타임이 줄면 아래에서 위로 사라진다.
- 스킬이 잠겨 있는 스테이지에서는 아이콘 위에 자물쇠를 그려서 쓸 수 없다는 것을 보여 준다.

모든 UI 그림은 화면 전체 크기 기준이며, UI_SCALE 로 줄여서 왼쪽 아래 모서리에 맞춘다.
"""

import math
import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "sprites", "UI")
BACKGROUND_FILE = os.path.join(UI_DIR, "UI_background.png")
HP_FILE = os.path.join(UI_DIR, "hp_{}.png")
SKILL_TIME_FILE = os.path.join(UI_DIR, "skill_time.png")
KILL_ICON_FILE = os.path.join(UI_DIR, "killcounter.png")
MAX_HP = 5
UI_SCALE = 0.75  # UI 그림의 화면 배율(원래 크기 대비)

# skill_time.png 에서 회색 원이 차지하는 범위(원본 1920x1080 기준, 왼쪽/위가 0)
SKILL_DISC_TOP = 918
SKILL_DISC_BOTTOM = 1060
SKILL_DISC_LEFT = 397
SKILL_DISC_RIGHT = 538
SKILL_SRC_W = 1920
SKILL_SRC_H = 1080

# 잠금 표시(자물쇠): sprites 에 그림이 없으므로 도형으로 한 번 구워서 쓴다.
LOCK_TEX = 128  # 구울 때의 해상도(줄여서 그리면 선이 부드러워진다)
LOCK_COLOR = (255, 236, 190)
LOCK_HOLE = (26, 26, 34)

_images = {}


def skill_icon_center(width, height):
    """스킬 아이콘(회색 원)의 화면 중심. y 는 pico2d 좌표(아래가 0).

    UI 그림은 화면의 왼쪽 아래 모서리에 붙여서 그리므로, y 는 그림의 아래쪽에서 잰다.
    """
    sx = (width * UI_SCALE) / SKILL_SRC_W
    sy = (height * UI_SCALE) / SKILL_SRC_H
    cx = (SKILL_DISC_LEFT + SKILL_DISC_RIGHT) * 0.5 * sx
    cy = height * UI_SCALE - (SKILL_DISC_TOP + SKILL_DISC_BOTTOM) * 0.5 * sy
    return cx, cy


def _lock_image(art):
    """잠금 표시용 자물쇠 그림(한 번만 굽는다)."""

    def paint():
        size = LOCK_TEX
        cx = size * 0.5
        # 고리: 위쪽 반원. 몸통을 나중에 덮어 아래쪽은 가려진다.
        ring_cy = size * 0.64
        ring_r = int(size * 0.23)
        for k in range(9):
            pico2d.draw_circle(cx, ring_cy, ring_r - k, *LOCK_COLOR,
                               filled=False)
        # 몸통: 위아래 모서리가 둥근 사각형.
        left, right = size * 0.22, size * 0.78
        bottom, top = size * 0.10, size * 0.53
        corner = size * 0.11
        y = int(bottom)
        while y <= int(top):
            dx = 0.0
            if y < bottom + corner:
                dy = bottom + corner - y
                dx = corner - math.sqrt(max(0.0, corner * corner - dy * dy))
            if y > top - corner:
                dy = y - (top - corner)
                dx = max(dx, corner - math.sqrt(
                    max(0.0, corner * corner - dy * dy)))
            pico2d.draw_line(left + dx, y, right - dx, y, *LOCK_COLOR)
            y += 1
        # 열쇠 구멍.
        hole_y = size * 0.31
        pico2d.draw_circle(cx, hole_y, int(size * 0.06), *LOCK_HOLE,
                           filled=True)
        pico2d.draw_rectangle(cx - size * 0.025, hole_y - size * 0.10,
                              cx + size * 0.025, hole_y, *LOCK_HOLE,
                              filled=True)

    return art.bake("ui_skill_lock", LOCK_TEX, LOCK_TEX, paint)


def _image(path):
    """UI 그림을 처음 쓸 때 한 번만 읽는다(창이 열린 뒤에 읽어야 한다)."""
    if path not in _images:
        _images[path] = pico2d.load_image(path)
    return _images[path]


def kill_icon():
    return _image(KILL_ICON_FILE)


class HUDOverlay:
    def draw(self, art, width, height, hp, cooldown_ratio=0.0,
             dash_locked=False):
        ui_w = width * UI_SCALE
        ui_h = height * UI_SCALE
        art.blit_to(_image(BACKGROUND_FILE), 0, 0, ui_w, ui_h)
        lost = max(0, min(MAX_HP, MAX_HP - hp))
        for k in range(1, lost + 1):
            art.blit_to(_image(HP_FILE.format(k)), 0, 0, ui_w, ui_h)
        self._draw_skill_time(art, width, height, cooldown_ratio)
        if dash_locked:
            self._draw_lock(art, width, height)

    def _draw_lock(self, art, width, height):
        """대쉬가 잠겨 있을 때 스킬 아이콘 위에 자물쇠를 보여 준다."""
        cx, cy = skill_icon_center(width, height)
        # 아이콘을 살짝 어둡게 덮어 쓸 수 없는 스킬임을 보여 준다.
        art.blit(art.disc((8, 8, 12)), cx, cy, 66, 66, alpha=150)
        art.blit(_lock_image(art), cx, cy - 1, 42, 42)

    def _draw_skill_time(self, art, width, height, cooldown_ratio):
        """스킬을 쓰면 나타나고, 쿨타임이 줄면 원이 아래에서 위로 사라진다(cooldown_ratio 0~1, 0이면 안 그림)."""
        ratio = max(0.0, min(1.0, cooldown_ratio))
        if ratio <= 0.0:
            return
        image = _image(SKILL_TIME_FILE)
        ui_w = width * UI_SCALE
        ui_h = height * UI_SCALE
        # 원 윗부분은 남기고, 아래쪽부터 잘라낸다.
        cut = int(SKILL_DISC_TOP + (SKILL_DISC_BOTTOM - SKILL_DISC_TOP) * ratio)
        scale = ui_h / SKILL_SRC_H
        top = height - ui_h  # 그림 윗변의 화면 y(SDL 좌표, 위에서 아래로)
        src = pico2d.SDL_Rect(0, 0, image.w, cut)
        dst = pico2d.SDL_Rect(0, int(top), int(ui_w), int(cut * scale))
        pico2d.SDL_RenderCopy(art.renderer, image.texture, src, dst)
