"""높은 발판의 그림: 상자.

상자 밑면은 캐릭터가 서는 지면 높이(contact_y)에 맞춘다.
원래 크기의 1.5배에서 1.2배 더 키운 크기다.
1층과 2층의 윗면이 밟을 수 있는 발판이다.
그림마다 행과 가로 범위가 다르므로 이미지별 레이아웃을 따로 둔다.
"""

import os

from props import PROP_SCALE, Prop

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECT_DIR = os.path.join(BASE_DIR, "sprites", "object")
BOX_SCALE = PROP_SCALE * 1.5 * 1.2

# 이미지 파일 이름 -> (밑면 행, 1층 윗면 행, 1층 가로 범위, 2층 윗면 행, 2층 가로 범위).
# 행은 원본 이미지 윗줄 기준이다.
BOX_LAYOUTS = {
    "box2.png": (836, 540, (410, 843), 231, (236, 839)),
    "box_stage2.png": (836, 541, (410, 770), 231, (236, 839)),
}
DEFAULT_BOX_FILE = "box2.png"


class Box(Prop):
    def __init__(self, contact_y, file_name=DEFAULT_BOX_FILE):
        bottom_row, *_ = BOX_LAYOUTS[file_name]
        super().__init__(os.path.join(OBJECT_DIR, file_name),
                         bottom_row=bottom_row,
                         scale=BOX_SCALE, contact_y=contact_y)
        self.layout = BOX_LAYOUTS[file_name]

    def level_surface(self, level):
        """level(1 또는 2)의 (그림 중심 기준 왼쪽 오프셋, 너비, 윗면 y)."""
        _, row1, x1_range, row2, x2_range = self.layout
        row, (x0, x1) = (row1, x1_range) if level == 1 else (row2, x2_range)
        left = (x0 - 512) * self.scale
        width = (x1 - x0) * self.scale
        return left, width, self.row_y(row, 0)
