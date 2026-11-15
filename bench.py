"""낮은 발판의 그림: 벤치.

벤치는 바닥(도로 윗면)에 놓이고, 원래 그림자를 그대로 쓴다.
앉는 면의 윗면이 밟을 수 있는 발판이다.
"""

import os

from props import PROP_SCALE, Prop

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BENCH_FILE = os.path.join(BASE_DIR, "bench.png")
BENCH_BOTTOM_ROW = 788  # 벤치 다리 아랫면(원본 이미지 윗줄 기준)
BENCH_OFFSET = -10  # 바닥보다 10px 더 아래
SEAT_ROW = 565  # 앉는 면 윗줄(원본 이미지 윗줄 기준)
SEAT_X = (150, 874)  # 앉는 면 가로 범위(원본 x, 팔걸이 제외)


class Bench(Prop):
    def __init__(self):
        super().__init__(BENCH_FILE, bottom_row=BENCH_BOTTOM_ROW,
                         base_offset=BENCH_OFFSET, scale=PROP_SCALE,
                         key_shadow=False)

    def seat_surface(self, ground_y):
        """(왼쪽 x 오프셋, 너비, 윗면 y): 그림 중심 기준 오프셋과 너비(px)."""
        x0, x1 = SEAT_X
        left = (x0 - 512) * self.scale
        width = (x1 - x0) * self.scale
        return left, width, self.row_y(SEAT_ROW, ground_y)
