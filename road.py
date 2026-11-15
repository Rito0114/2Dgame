"""바닥(도로) 그림.

road.png 의 포장 윗면을 지면 높이에 맞춰 그린다.
땅 블록은 텍스처로 한 번 구워서 재사용한다.
"""

import pico2d

# 이미지 아래쪽에서 포장 윗면까지의 높이(px)
ROAD_TOP = 152
# 땅 블록 가장자리의 그림자 폭(px)
EDGE_SHADE = 10


class Road:
    def __init__(self, path):
        self.path = path
        self._image = None

    @property
    def image(self):
        # 창이 열린 뒤에 불러야 하므로 처음 쓸 때 읽는다.
        if self._image is None:
            self._image = pico2d.load_image(self.path)
        return self._image

    @property
    def w(self):
        return self.image.w

    @property
    def h(self):
        return self.image.h

    def ground(self, art, left, bottom, width, height, ground_y, base_color):
        """땅 블록 한 개를 구운 텍스처를 돌려준다.

        left 는 월드 x, bottom 은 블록 아래쪽 y 이다.
        포장 윗면이 ground_y 에 오도록 그림을 맞추고, 가로로는 월드 좌표에
        맞춰 이어 붙인다.
        """
        road = self.image
        road_bottom = (ground_y - ROAD_TOP) - bottom
        road_y = height - road_bottom - road.h

        def paint():
            pico2d.draw_rectangle(0, 0, width, height, *base_color,
                                  filled=True)
            x = -(int(left) % road.w)
            while x < width:
                pico2d.SDL_RenderCopy(
                    art.renderer, road.texture, None,
                    pico2d.SDL_Rect(int(x), int(road_y), road.w, road.h),
                )
                x += road.w
            # 구멍과 맞닿는 가장자리를 어둡게 해서 절벽처럼 보이게 한다.
            for i in range(EDGE_SHADE):
                alpha = int(200 * (1.0 - i / EDGE_SHADE))
                pico2d.draw_rectangle(i, 0, i + 1, height, 8, 10, 24,
                                      alpha, filled=True)
                pico2d.draw_rectangle(width - i - 1, 0, width - i, height,
                                      8, 10, 24, alpha, filled=True)

        key = ("ground", width, height, int(left) % road.w, base_color)
        return art.bake(key, width, height, paint)

    def draw_top(self, art, x, ground_y):
        """포장 윗면이 ground_y 에 오도록 (x 부터) 그린다. 무대 바닥용."""
        art.blit_to(self.image, x, ground_y - ROAD_TOP, self.w, self.h)
