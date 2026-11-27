"""보스 전용 스프라이트 시트와 프레임 애니메이션.

sprites/boss/ 아래의 Boss_*.png 는 모두 가로줄 여러 개의 프레임으로 이루어진
시트다. 시트마다 칸 크기와 발바닥 위치가 다르므로 여기에서 한 번에 정의해
보스 상태와 관계없이 같은 방식으로 그릴 수 있게 한다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SPRITE_DIR = os.path.join(BASE_DIR, "sprites", "boss")

# 주인공(idle_sprite.png 첫 프레임: 원본 431px * SCALE 0.38)의 화면상 보이는 높이.
# 모든 보스 애니메이션의 가장 큰 프레임이 이 높이가 되도록 시트별 배율을 정한다.
PLAYER_VISIBLE_HEIGHT = 164.0


class BossSprite:
    """한 장의 애니메이션 시트."""

    def __init__(self, filename, cols, rows, frame_time, foot_pads,
                 visible_height, mirror=False):
        self.path = os.path.join(SPRITE_DIR, filename)
        self.cols = cols
        self.rows = rows
        self.frame_time = frame_time
        self.foot_pads = foot_pads
        self.frames = cols * rows
        self.duration = frame_time * self.frames
        # 시트마다 칸 크기와 그림 크기가 달라 보이는 크기가 제각각이었다.
        # 프레임에서 가장 큰 보이는 높이를 주인공 높이에 맞춰 스케일을 보정한다.
        self.visible_height = float(visible_height)
        self.scale = PLAYER_VISIBLE_HEIGHT / self.visible_height
        self.mirror = mirror  # True 이면 다른 애니메이션과 좌우반전이 반대다
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
        """(x, y) 를 발밑 중앙으로 해서 주인공 크기로 한 프레임을 그린다."""
        frame = self.frame_at(t)
        left, bottom, width, height = self.cell(frame)
        foot = self.foot_pads[frame]
        # scale 은 외부에서 곱하는 추가 배율. 기본값 1 이 시트 보정 배율이다.
        draw_scale = scale * self.scale
        center_x = x - camera_x + shake_x
        center_y = y - foot * draw_scale + height * draw_scale * 0.5
        flip = "h" if (facing < 0) != self.mirror else ""
        self.image().clip_composite_draw(
            left, bottom, width, height, 0.0, flip,
            center_x, center_y, width * draw_scale, height * draw_scale,
        )
        return frame


# foot_pads: 각 프레임의 칸 아래쪽에서 발바닥까지의 거리(원본 px).
# 행마다 그림이 어긋나 있어 프레임별로 측정해 두어야 발이 흔들리지 않는다.
# visible_height: 시트에서 가장 큰 프레임의 보이는 높이(원본 px, alpha>8 기준).
# 시트마다 이 값이 달라 같은 배율로 그리면 크기가 제각각이 되었다.
BOSS_SPRITES = {
    "idle": BossSprite(
        "Boss_Idle.png", 5, 2, 0.12,
        (41, 41, 41, 41, 41, 70, 70, 70, 71, 70), 340, mirror=True),
    "walk": BossSprite(
        "Boss_Walk.png", 4, 2, 0.10,
        (16, 18, 19, 18, 17, 16, 15, 14), 371),
    "rising": BossSprite(
        "Boss_Rising.png", 5, 2, 0.10,
        (35, 39, 40, 0, 0, 28, 28, 28, 28, 28), 334),
    "hit": BossSprite(
        "Boss_Hit.png", 5, 2, 0.06,
        (13, 13, 14, 18, 40, 20, 23, 22, 22, 18), 330),
    "hurt": BossSprite(
        "Boss_Hurt.png", 5, 2, 0.08,
        (27, 27, 27, 27, 27, 26, 22, 23, 24, 26), 401),
    "fire": BossSprite(
        "Boss_Fire.png", 5, 2, 0.08,
        (27, 27, 27, 28, 28, 26, 26, 26, 25, 25), 312),
    "knife": BossSprite(
        "Boss_Knife.png", 5, 2, 0.08,
        (15, 15, 15, 15, 15, 19, 20, 19, 17, 16), 330),
    "throw": BossSprite(
        "Boss_Throw.png", 5, 2, 0.08,
        (10, 13, 14, 14, 16, 15, 15, 15, 15, 15), 335),
    "skill1": BossSprite(
        "Boss_Skill1.png", 5, 2, 0.08,
        (29, 30, 34, 38, 40, 36, 32, 28, 28, 29), 323),
    "skill2": BossSprite(
        "Boss_Skill2.png", 5, 2, 0.08,
        (24, 24, 28, 28, 30, 32, 29, 30, 27, 29), 327),
    "skill3": BossSprite(
        "Boss_Skill3.png", 5, 2, 0.08,
        (7, 7, 7, 10, 33, 38, 39, 39, 39, 38), 342),
    "retire": BossSprite(
        "Boss_Retire.png", 5, 2, 0.09,
        (9, 10, 10, 10, 9, 32, 32, 32, 31, 30), 344),
    "retire2": BossSprite(
        "Boss_Retire2.png", 5, 2, 0.09,
        (5, 6, 7, 6, 2, 18, 20, 20, 22, 22), 353),
}

IDLE = BOSS_SPRITES["idle"]
ATTACK_NAMES = ("fire", "knife", "throw", "skill1", "skill2", "skill3")
