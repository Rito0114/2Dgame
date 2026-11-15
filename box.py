"""높은 발판의 그림: 상자.

상자 밑면은 캐릭터가 서는 지면 높이(contact_y)에 맞춘다.
원래 크기의 1.5배에서 1.2배 더 키운 크기다.
1층과 2층의 윗면이 밟을 수 있는 발판이다.
"""

import os

from props import PROP_SCALE, Prop

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOX_FILE = os.path.join(BASE_DIR, "sprites", "object", "box2.png")
BOX_BOTTOM_ROW = 836  # 상자 밑면(원본 이미지 윗줄 기준)
BOX_SCALE = PROP_SCALE * 1.5 * 1.2
# (윗면 행, 가로 범위) — 원본 이미지 기준. 1층은 오른쪽 상자의 윗면만 있다.
LEVEL1 = (540, (410, 843))
LEVEL2 = (231, (236, 839))


class Box(Prop):
    def __init__(self, contact_y):
        super().__init__(BOX_FILE, bottom_row=BOX_BOTTOM_ROW,
                         scale=BOX_SCALE, contact_y=contact_y)

    def level_surface(self, level):
        """level(1 또는 2)의 (왼쪽 x 오프셋, 너비, 윗면 y)."""
        row, (x0, x1) = LEVEL1 if level == 1 else LEVEL2
        left = (x0 - 512) * self.scale
        width = (x1 - x0) * self.scale
        return left, width, self.row_y(row, 0)
