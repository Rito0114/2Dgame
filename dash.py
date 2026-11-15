"""주인공 대쉬 스킬 (Q): sprites/girl/sandebistan.png.

시트는 3148x5746 이고, 한 열에 17개의 프레임이 세로로 쌓여 있다.
프레임 k 는 대쉬하는 캐릭터와 그 뒤로 남는 잔상 k 개를 그린 것이다.
그래서 가장 오른쪽(바라보는 쪽) 캐릭터의 몸 중심을 실제 캐릭터 위치에 맞춘다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASH_FILE = os.path.join(BASE_DIR, "sprites", "girl", "sandebistan.png")

# 프레임별 (윗줄, 아랫줄, 가장 왼쪽 픽셀, 가장 오른쪽 픽셀) - 원본 이미지 기준.
# 그림은 가장 왼쪽 픽셀을 고정 기준으로 그리고, 카메라와 피격 판정은 가장 오른쪽(앞쪽) 픽셀을 쓴다.
BANDS = (
    (60, 304, 103, 259), (380, 632, 102, 297), (712, 964, 103, 333),
    (1048, 1300, 102, 393), (1380, 1632, 103, 459), (1716, 1968, 103, 570),
    (2052, 2304, 103, 722), (2381, 2633, 103, 913), (2712, 2964, 103, 1183),
    (3040, 3292, 103, 1500), (3367, 3619, 103, 1823), (3720, 3977, 103, 2071),
    (4047, 4306, 102, 2224), (4374, 4637, 102, 2321), (4701, 4969, 103, 2380),
    (5024, 5300, 103, 2414), (5351, 5627, 103, 2441),
)
FRAME_TIME = 0.0375  # 프레임당 시간(기존 0.025 의 1.5배)
DURATION = FRAME_TIME * len(BANDS)
SCALE = 0.55  # 원본 이미지를 화면 크기로 줄이는 배율
CROP_LEFT = 60  # 잘라 쓰는 가로 범위(원본 x)
CROP_W = 2420
CROP_CENTER = CROP_LEFT + CROP_W * 0.5

_sheet = None


def _load():
    global _sheet
    if _sheet is None:
        _sheet = pico2d.load_image(DASH_FILE)
    return _sheet


LAST_FRAME_ELAPSED = (len(BANDS) - 1) * FRAME_TIME


def lead_offset(elapsed, facing):
    """가장 왼쪽 픽셀에서 가장 오른쪽(앞쪽) 픽셀까지의 화면 거리. 바라보는 방향을 따른다."""
    frame = min(int(elapsed / FRAME_TIME), len(BANDS) - 1)
    _, _, xmin, xmax = BANDS[frame]
    return facing * (xmax - xmin) * SCALE


SKILL_BG_FILE = os.path.join(BASE_DIR, "sprites", "object", "skill_background.png")
_skill_bg = None


class SkillBackground:
    """스킬 배경. 스킬을 쓰는 동안 나타나고, 끝나면 사라진다. 나타날 때와 사라질 때 0.5초 페이드."""

    FADE_TIME = 0.5
    MAX_ALPHA = 128  # 최대 불투명도(0~255). 약 50%

    def __init__(self):
        self.alpha = 0.0

    def update(self, dt, active):
        target = self.MAX_ALPHA if active else 0.0
        step = self.MAX_ALPHA * dt / self.FADE_TIME
        if self.alpha < target:
            self.alpha = min(target, self.alpha + step)
        else:
            self.alpha = max(target, self.alpha - step)

    def draw(self, art, width, height):
        if self.alpha < 1.0:
            return
        global _skill_bg
        if _skill_bg is None:
            _skill_bg = pico2d.load_image(SKILL_BG_FILE)
        art.blit_to(_skill_bg, 0, 0, width, height, int(self.alpha))


def draw_dash(x, y, facing, elapsed):
    """대쉬 프레임 한 장을 그린다. (x, y) 는 캐릭터 몸 중심과 발밑(화면 좌표)."""
    sheet = _load()
    frame = min(int(elapsed / FRAME_TIME), len(BANDS) - 1)
    top, bottom, xmin, _ = BANDS[frame]
    height = bottom - top + 1
    # 각 프레임의 가장 왼쪽 픽셀이 x 에 오도록 그림 중심을 옮긴다. 뒤집히면 방향도 반대다.
    center_x = x - facing * (xmin - CROP_CENTER) * SCALE
    center_y = y + height * SCALE * 0.5
    flip = "h" if facing < 0 else ""
    sheet.clip_composite_draw(
        CROP_LEFT, sheet.h - bottom - 1, CROP_W, height, 0.0, flip,
        center_x, center_y, CROP_W * SCALE, height * SCALE,
    )
