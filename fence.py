"""도로 위 울타리.

fence.png 를 땅 구간마다 따로 구워서 그린다. 구멍(pit) 위에는 그리지 않으므로
울타리도 땅과 함께 끊긴다.
"""

import pico2d

# 이미지 아래쪽에서 울타리 아랫단까지의 높이(px). road.png 와 같은 기준이다.
FENCE_BASE = 152
# 원본 이미지(4344x724)를 줄여서 쓰는 비율.
FENCE_SCALE = 1.125


class Fence:
    def __init__(self, path):
        self.path = path
        self._image = None

    @property
    def image(self):
        # 창이 열린 뒤에 불러야 하므로 처음 쓸 때 읽는다.
        if self._image is None:
            self._image = pico2d.load_image(self.path)
        return self._image

    def segment(self, art, left, width):
        """땅 구간 하나만큼의 울타리 텍스처를 돌려준다. left 는 월드 x."""
        fence = self.image
        scale = FENCE_SCALE
        tile_w = int(fence.w * scale)
        tile_h = int(fence.h * scale)
        out_w = int(width)

        def paint():
            x = -(int(left) % tile_w)
            while x < out_w:
                pico2d.SDL_RenderCopy(
                    art.renderer, fence.texture, None,
                    pico2d.SDL_Rect(int(x), 0, tile_w, tile_h),
                )
                x += tile_w

        key = ("fence", out_w, int(left) % tile_w, tile_w, tile_h)
        return art.bake(key, out_w, tile_h, paint)

    def draw(self, art, left, width, x, ground_y):
        """구간을 화면 x 에 그린다. 울타리 아랫단이 ground_y 에 오도록 한다."""
        image = self.segment(art, left, width)
        art.blit_to(image, x, ground_y - FENCE_BASE * FENCE_SCALE,
                    width, image.h)
