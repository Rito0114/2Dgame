"""주인공 공격 이펙트: sprites/girl/punch_effect.png.

시트는 2172x724, 5열 x 2행(10프레임)이다. 공격 한 번에 10프레임을 한 번만 재생한다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUNCH_FILE = os.path.join(BASE_DIR, "sprites", "girl", "punch_effect.png")
COLS, ROWS = 5, 2
FRAME_TIME = 0.027  # 공격 모션(attack) 프레임 시간과 같다
DURATION = FRAME_TIME * 10
SCALE = 0.45  # 원본 셀(434x362)을 화면 크기로 줄이는 배율
# 캐릭터 기준 이펙트 중심 위치(화면 px). x 는 바라보는 방향으로, y 는 발밑에서 위로.
OFFSET_X = 80
OFFSET_Y = 110
# 화면 기준 추가 이동(px). 왼쪽은 음수, 아래쪽은 음수.
SHIFT_X = -20
SHIFT_Y = -20

_sheet = None


def _load():
    global _sheet
    if _sheet is None:
        _sheet = pico2d.load_image(PUNCH_FILE)
    return _sheet


def draw_punch(x, y, facing, elapsed):
    """이펙트 한 프레임을 그린다. (x, y) 는 캐릭터 발밑 중심(화면 좌표)."""
    if elapsed < 0.0 or elapsed >= DURATION:
        return
    sheet = _load()
    frame = min(int(elapsed / FRAME_TIME), 9)
    cell_w = sheet.w // COLS
    cell_h = sheet.h // ROWS
    col = frame % COLS
    row = frame // COLS
    left = col * cell_w
    bottom = sheet.h - (row + 1) * cell_h
    width = cell_w * SCALE
    height = cell_h * SCALE
    flip = "h" if facing < 0 else ""
    sheet.clip_composite_draw(
        left, bottom, cell_w, cell_h, 0.0, flip,
        x + facing * OFFSET_X + SHIFT_X, y + OFFSET_Y + SHIFT_Y, width, height,
    )
