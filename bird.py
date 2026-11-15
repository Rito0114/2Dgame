"""날아다니는 적 (위습 대체): 새 수인.

- 좌우 이동: sprites/bird/bird_fly.png
- 접촉(공격): sprites/bird/bird_attack.png
- 사망: sprites/bird/bird_retire.png (지면까지 떨어지면서 재생)

fly / attack 시트는 1983x793, retire2 시트는 2200x800 이고, 모두 5열 x 2행(10프레임)이다.
사망 시트는 셀이 440x400 이라 셀 크기를 따로 쓴다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "sprites", "bird")
FLY_FILE = os.path.join(SPRITE_DIR, "bird_fly.png")
ATTACK_FILE = os.path.join(SPRITE_DIR, "bird_attack2.png")
RETIRE_FILE = os.path.join(SPRITE_DIR, "bird_retire2.png")
COLS, ROWS = 5, 2
CELL_H = 400  # 사망 시트의 셀 높이(원본 픽셀)
CELL_INSET = 3  # 셀 가장자리에서 잘라낼 픽셀 수(가로)

# 화면에 그릴 때 배율(곰과 같은 크기 기준)
SCALE = 0.42
# 충돌 크기(화면에 보이는 몸통 기준)
BIRD_WIDTH = 80
BIRD_HEIGHT = 80

FLY_FRAME_TIME = 0.09
ATTACK_FRAME_TIME = 0.06
RETIRE_FRAME_TIME = 0.09
# 사망 시 떨어지는 시간: 사망 모션 한 바퀴와 같다.
FALL_TIME = RETIRE_FRAME_TIME * 10
# 접촉 중 공격 모션을 유지하는 시간
# 공격 모션은 한 번만 재생한다(10프레임). 접촉이 끊긴 뒤 이 시간이 지나야 다시 공격한다.
ATTACK_DURATION = ATTACK_FRAME_TIME * 10
ATTACK_HOLD = 0.1
# 사망 모션이 끝난 뒤 이 시간이 지나면 화면에서 사라진다.
DEATH_TIME = FALL_TIME + 0.4

# 비행/공격: 몸 아래쪽이 셀 아래에서 떨어진 높이(원본 px). 사망 시작 위치와 맞춘다.
FLY_PAD = 40

# 사망: 프레임마다 내용 아래쪽이 셀 아래에서 떨어진 높이(원본 px).
# 바닥에 닿는 기준선이다.
RETIRE_PAD = (42, 37, 39, 13, 1, 40, 43, 42, 39, 39)

_sheets = {}


def _sheet(path):
    if path not in _sheets:
        _sheets[path] = pico2d.load_image(path)
    return _sheets[path]


def _cell(sheet, frame, row_top, row_height):
    """프레임의 (left, bottom, width, height). 세로는 row_top 부터 row_height 만큼."""
    col = frame % COLS
    left = int(round(col * sheet.w / COLS))
    right = int(round((col + 1) * sheet.w / COLS))
    return (left + CELL_INSET, sheet.h - row_top - row_height,
            right - left - 2 * CELL_INSET, row_height)


def draw_bird(x, y, facing, state, t, camera_x=0.0, shake_x=0.0):
    """새를 그린다. (x, y) 는 몸통 중심 좌표. state 는 fly / attack / retire."""
    center_x = x - camera_x + shake_x
    flip = "h" if facing < 0 else ""

    if state == "retire":
        sheet = _sheet(RETIRE_FILE)
        frame = min(int(t / RETIRE_FRAME_TIME), 9)
        row = frame // COLS
        left, bottom, width, height = _cell(sheet, frame, row * CELL_H, CELL_H)
        # y 는 바닥 접점(내용 아래쪽)이다.
        center_y = y + CELL_H * SCALE * 0.5 - RETIRE_PAD[frame] * SCALE
    else:
        if state == "attack":
            path, frame = ATTACK_FILE, min(int(t / ATTACK_FRAME_TIME), 9)
        else:
            path, frame = FLY_FILE, int(t / FLY_FRAME_TIME) % 10
        sheet = _sheet(path)
        row = frame // COLS
        cell_h = sheet.h // ROWS
        left, bottom, width, height = _cell(sheet, frame, row * cell_h, cell_h)
        center_y = y + cell_h * SCALE * 0.5 - FLY_PAD * SCALE

    sheet.clip_composite_draw(
        left, bottom, width, height, 0.0, flip,
        center_x, center_y, width * SCALE, height * SCALE,
    )
