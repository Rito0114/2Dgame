"""고양이 적 (스테이지 2 전용).

- 걷기: sprites/cat/cat_walk.png (1984x793, 5열 x 2행, 10프레임)
- 공격: sprites/cat/cat_fire.png (2172x724, 5열 x 2행, 10프레임)
- 사망: sprites/cat/cat_retire.png (2172x724, 5열 x 2행, 10프레임)

땅 위를 좌우로 걷고, 접촉하면 공격 모션을 한 번 재생한다.
쓰러지면 사망 모션을 재생한 뒤 사라진다.
시트마다 그림의 크기가 다르므로, 서 있을 때의 키가 걷기와 같도록 배율을 따로 둔다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "sprites", "cat")
WALK_FILE = os.path.join(SPRITE_DIR, "cat_walk.png")
FIRE_FILE = os.path.join(SPRITE_DIR, "cat_fire.png")
RETIRE_FILE = os.path.join(SPRITE_DIR, "cat_retire.png")
COLS, ROWS = 5, 2
CELL_INSET = 3  # 셀 가장자리에서 잘라낼 픽셀 수(원본 기준)

# 충돌 크기(화면에 보이는 몸통 기준)
CAT_WIDTH = 93
CAT_HEIGHT = 150

# 시트별 배율. 서 있는 자세의 키가 걷기(0.42)와 같아지도록 맞췄다.
WALK_SCALE = 0.42
FIRE_SCALE = 0.52
RETIRE_SCALE = 0.43

# 프레임마다 발바닥이 셀 아래쪽에서 떨어진 높이(원본 px). 발이 땅에 붙도록 보정한다.
WALK_PAD = (25, 30, 30, 35, 34, 40, 29, 27, 27, 25)
FIRE_PAD = (45, 46, 45, 45, 46, 47, 47, 47, 46, 46)
RETIRE_PAD = (1, 1, 1, 1, 1, 33, 30, 30, 31, 31)

WALK_FRAME_TIME = 0.1
ATTACK_FRAME_TIME = 0.05
RETIRE_FRAME_TIME = 0.09
ATTACK_DURATION = ATTACK_FRAME_TIME * 10  # 공격 모션은 한 번만 재생한다
RETIRE_DURATION = RETIRE_FRAME_TIME * 10

_sheets = {}


def _sheet(path):
    if path not in _sheets:
        _sheets[path] = pico2d.load_image(path)
    return _sheets[path]


def _draw_frame(sheet, frame, pads, scale, x, y, facing, camera_x, shake_x):
    """시트의 frame 번째 칸을 발밑 중앙 (x, y) 기준으로 그린다."""
    col = frame % COLS
    row = frame // COLS
    cell_w = sheet.w / COLS
    cell_h = sheet.h / ROWS
    left = int(round(col * cell_w)) + CELL_INSET
    right = int(round((col + 1) * cell_w))
    width = right - int(round(col * cell_w)) - 2 * CELL_INSET
    band_top = int(round(row * cell_h))
    band_bottom = int(round((row + 1) * cell_h))
    height = band_bottom - band_top - 2 * CELL_INSET
    bottom = sheet.h - band_bottom + CELL_INSET

    draw_w = width * scale
    draw_h = height * scale
    center_x = x - camera_x + shake_x
    center_y = y + draw_h * 0.5 - (pads[frame] - CELL_INSET) * scale
    flip = "h" if facing < 0 else ""
    sheet.clip_composite_draw(
        left, bottom, width, height, 0.0, flip,
        center_x, center_y, draw_w, draw_h,
    )


def draw_walk(x, y, facing, t, camera_x=0.0, shake_x=0.0):
    frame = int(t / WALK_FRAME_TIME) % 10
    _draw_frame(_sheet(WALK_FILE), frame, WALK_PAD, WALK_SCALE,
                x, y, facing, camera_x, shake_x)


def draw_attack(x, y, facing, t, camera_x=0.0, shake_x=0.0):
    frame = min(int(t / ATTACK_FRAME_TIME), 9)
    _draw_frame(_sheet(FIRE_FILE), frame, FIRE_PAD, FIRE_SCALE,
                x, y, facing, camera_x, shake_x)


def draw_retire(x, y, facing, t, camera_x=0.0, shake_x=0.0):
    frame = min(int(t / RETIRE_FRAME_TIME), 9)
    _draw_frame(_sheet(RETIRE_FILE), frame, RETIRE_PAD, RETIRE_SCALE,
                x, y, facing, camera_x, shake_x)
