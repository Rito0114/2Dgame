"""낮은 발판의 그림: 벤치.

벤치는 바닥(도로 윗면)에 놓이고, 원래 그림자를 그대로 쓴다.
앉는 면의 윗면이 밟을 수 있는 발판이다.
그림마다 바닥 행과 앉는 면 행이 다르므로 이미지별 레이아웃을 따로 둔다.
"""

import os

from props import PROP_SCALE, Prop

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECT_DIR = os.path.join(BASE_DIR, "sprites", "object")
BENCH_OFFSET = -10  # 바닥보다 10px 더 아래

# 이미지 파일 이름 -> (바닥 행, 앉는 면 행, 앉는 면 가로 범위). 행은 원본 이미지 윗줄 기준.
BENCH_LAYOUTS = {
    "bench.png": (788, 565, (150, 874)),
    "bench_stage2.png": (786, 564, (105, 915)),
}
DEFAULT_BENCH_FILE = "bench.png"


class Bench(Prop):
    def __init__(self, file_name=DEFAULT_BENCH_FILE):
        bottom_row, seat_row, seat_x = BENCH_LAYOUTS[file_name]
        super().__init__(os.path.join(OBJECT_DIR, file_name),
                         bottom_row=bottom_row,
                         base_offset=BENCH_OFFSET, scale=PROP_SCALE,
                         key_shadow=False)
        self.seat_row = seat_row
        self.seat_x = seat_x

    def seat_surface(self, ground_y):
        """(그림 중심 기준 왼쪽 오프셋, 너비, 윗면 y)."""
        x0, x1 = self.seat_x
        left = (x0 - 512) * self.scale
        width = (x1 - x0) * self.scale
        return left, width, self.row_y(self.seat_row, ground_y)
