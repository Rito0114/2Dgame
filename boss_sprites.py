"""보스 전용 스프라이트 시트와 프레임 애니메이션.

sprites/boss/ 아래의 Boss_*.png 는 모두 가로줄 여러 개의 프레임으로 이루어진
시트다. 시트마다 칸 크기와 발바닥 위치가 다르므로 여기에서 한 번에 정의해
보스 상태와 관계없이 같은 방식으로 그릴 수 있게 한다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "sprites", "boss")


class BossSprite:
    """한 장의 애니메이션 시트."""

    def __init__(self, filename, cols, rows, frame_time, foot_pads):
        self.path = os.path.join(SPRITE_DIR, filename)
        self.cols = cols
        self.rows = rows
        self.frame_time = frame_time
        self.foot_pads = foot_pads
        self.frames = cols * rows
        self.duration = frame_time * self.frames
        self._image = None

    def image(self):
        if self._image is None:
            self._image = pico2d.load_image(self.path)
        return self._image

    def cell(self, frame):
        """프레임의 (left, bottom, width, height). pico2d 좌표계."""
        sheet = self.image()
        col = frame % self.cols
        row = frame // self.cols
        left = int(round(col * sheet.w / self.cols))
        right = int(round((col + 1) * sheet.w / self.cols))
        top = int(round(row * sheet.h / self.rows))
        bottom_row = int(round((row + 1) * sheet.h / self.rows))
        return left, sheet.h - bottom_row, right - left, bottom_row - top

    def frame_at(self, t):
        return int(max(0.0, t) / self.frame_time) % self.frames

    def draw(self, x, y, facing, t, camera_x=0.0, shake_x=0.0, scale=1.0):
        """(x, y) 를 발밑 중앙으로 해서 한 프레임을 그린다."""
        frame = self.frame_at(t)
        left, bottom, width, height = self.cell(frame)
        foot = self.foot_pads[frame]
        center_x = x - camera_x + shake_x
        center_y = y - foot * scale + height * scale * 0.5
        flip = "h" if facing < 0 else ""
        self.image().clip_composite_draw(
            left, bottom, width, height, 0.0, flip,
            center_x, center_y, width * scale, height * scale,
        )
        return frame


# foot_pads: 각 프레임의 칸 아래쪽에서 발바닥까지의 거리(원본 px).
# 행마다 그림이 어긋나 있어 프레임별로 측정해 두어야 발이 흔들리지 않는다.
BOSS_SPRITES = {
    "idle": BossSprite(
        "Boss_Idle.png", 5, 2, 0.12,
        (41, 41, 41, 41, 41, 70, 70, 70, 71, 70)),
    "walk": BossSprite(
        "Boss_Walk.png", 4, 2, 0.10,
        (16, 18, 19, 18, 17, 16, 15, 14)),
    "rising": BossSprite(
        "Boss_Rising.png", 5, 2, 0.10,
        (35, 39, 40, 0, 0, 28, 28, 28, 28, 28)),
    "hit": BossSprite(
        "Boss_Hit.png", 5, 2, 0.06,
        (13, 13, 14, 18, 40, 20, 23, 22, 22, 18)),
    "fire": BossSprite(
        "Boss_Fire.png", 5, 2, 0.08,
        (27, 27, 27, 28, 28, 26, 26, 26, 25, 25)),
    "knife": BossSprite(
        "Boss_Knife.png", 5, 2, 0.08,
        (15, 15, 15, 15, 15, 19, 20, 19, 17, 16)),
    "throw": BossSprite(
        "Boss_Throw.png", 5, 2, 0.08,
        (10, 13, 14, 14, 16, 15, 15, 15, 15, 15)),
    "skill1": BossSprite(
        "Boss_Skill1.png", 5, 2, 0.08,
        (29, 30, 34, 38, 40, 36, 32, 28, 28, 29)),
    "skill2": BossSprite(
        "Boss_Skill2.png", 5, 2, 0.08,
        (24, 24, 28, 28, 30, 32, 29, 30, 27, 29)),
    "skill3": BossSprite(
        "Boss_Skill3.png", 5, 2, 0.08,
        (7, 7, 7, 10, 33, 38, 39, 39, 39, 38)),
    "retire": BossSprite(
        "Boss_Retire.png", 5, 2, 0.09,
        (9, 10, 10, 10, 9, 32, 32, 32, 31, 30)),
    "retire2": BossSprite(
        "Boss_Retire2.png", 5, 2, 0.09,
        (5, 6, 7, 6, 2, 18, 20, 20, 22, 22)),
}

IDLE = BOSS_SPRITES["idle"]
ATTACK_NAMES = ("fire", "knife", "throw", "skill1", "skill2", "skill3")
