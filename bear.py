"""곰 수인 적의 스프라이트 (슬라임 대체).

- 이동: sprites/bear/bear_walk.png
- 접촉(공격): sprites/bear/bear_attack.png
- 사망: sprites/bear/bear_retire2.png

walk / attack 시트는 1983x793, 5열 x 2행(10프레임)이다.
retire2 시트는 1983x900 이고, 두 줄의 그림이 셀 경계를 조금 넘어가므로
사망 프레임은 줄마다 따로 자른다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "sprites", "bear")
WALK_FILE = os.path.join(SPRITE_DIR, "bear_walk.png")
ATTACK_FILE = os.path.join(SPRITE_DIR, "bear_attack2.png")
RETIRE_FILE = os.path.join(SPRITE_DIR, "bear_retire2.png")
COLS, ROWS = 5, 2
CELL_INSET = 3  # 셀 가장자리에서 잘라낼 픽셀 수(원본 기준, 가로)

# 화면에 그릴 때 배율(원본 기준, 곰 키가 약 100px 이 되도록)
SCALE = 0.42
# 충돌 크기(화면에 보이는 몸통 기준)
BEAR_WIDTH = 93
BEAR_HEIGHT = 150

# 걷기/공격: 프레임마다 발바닥이 셀 아래쪽에서 떨어진 높이(원본 px)
WALK_PAD = (11, 13, 15, 11, 15, 17, 20, 22, 20, 18)
ATTACK_PAD = (17, 17, 17, 17, 16, 29, 29, 29, 29, 29)

# 사망: 줄마다 자르는 범위(원본 이미지 y, 위쪽 0 기준)
RETIRE_ROW_TOP = (0, 428)
RETIRE_ROW_BOTTOM = (420, 900)
# 사망: 프레임마다 자른 범위 아래쪽에서 발바닥까지의 높이(원본 px)
RETIRE_PAD = (11, 12, 9, 4, 0, 76, 77, 78, 79, 79)

WALK_FRAME_TIME = 0.1
ATTACK_FRAME_TIME = 0.05
RETIRE_FRAME_TIME = 0.09
# 사망 모션이 끝난 뒤 이 시간이 지나면 화면에서 사라진다.
DEATH_TIME = RETIRE_FRAME_TIME * COLS * ROWS + 0.4
# 접촉 중 공격 모션을 유지하는 시간
# 공격 모션은 한 번만 재생한다(10프레임). 접촉이 끊긴 뒤 이 시간이 지나야 다시 공격한다.
ATTACK_DURATION = ATTACK_FRAME_TIME * 10
ATTACK_HOLD = 0.1

_sheets = {}


def _sheet(path):
    if path not in _sheets:
        _sheets[path] = pico2d.load_image(path)
    return _sheets[path]


def _columns(sheet, frame, inset):
    col = frame % COLS
    left = int(round(col * sheet.w / COLS))
    right = int(round((col + 1) * sheet.w / COLS))
    return left + inset, right - left - 2 * inset


def _cell(sheet, frame):
    """walk / attack: 칸의 (left, bottom, width, height)."""
    row = frame // COLS
    left, width = _columns(sheet, frame, CELL_INSET)
    top = int(round(row * sheet.h / ROWS))
    bottom_row = int(round((row + 1) * sheet.h / ROWS))
    return left, sheet.h - bottom_row + CELL_INSET, width, bottom_row - top - 2 * CELL_INSET


def _retire_cell(sheet, frame):
    """retire: 줄마다 정해 둔 범위로 자른 (left, bottom, width, height)."""
    row = frame // COLS
    left, width = _columns(sheet, frame, CELL_INSET)
    top = RETIRE_ROW_TOP[row]
    bottom = RETIRE_ROW_BOTTOM[row]
    return left, sheet.h - bottom, width, bottom - top


def draw_bear(x, y, facing, state, t, camera_x=0.0, shake_x=0.0,
              scale=SCALE):
    """곰을 그린다. (x, y) 는 발밑 중앙 좌표. state 는 walk / attack / retire.

    scale 을 키우면 보스처럼 큰 곰을 그릴 수 있다.
    """
    center_x = x - camera_x + shake_x
    flip = "h" if facing < 0 else ""

    if state == "retire":
        sheet = _sheet(RETIRE_FILE)
        frame = min(int(t / RETIRE_FRAME_TIME), 9)
        left, bottom, width, height = _retire_cell(sheet, frame)
        # 발바닥까지의 높이는 자른 범위의 아래쪽 기준
        foot = RETIRE_PAD[frame]
    else:
        if state == "attack":
            path, pads, frame = ATTACK_FILE, ATTACK_PAD, min(int(t / ATTACK_FRAME_TIME), 9)
        else:
            path, pads, frame = WALK_FILE, WALK_PAD, int(t / WALK_FRAME_TIME) % 10
        sheet = _sheet(path)
        left, bottom, width, height = _cell(sheet, frame)
        # 패드는 셀 아래쪽 기준이고, 잘라낸 아래쪽은 CELL_INSET 만큼 위에 있다.
        foot = pads[frame] - CELL_INSET

    center_y = y + height * scale * 0.5 - foot * scale
    sheet.clip_composite_draw(
        left, bottom, width, height, 0.0, flip,
        center_x, center_y, width * scale, height * scale,
    )
