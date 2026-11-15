"""도로 위 울타리.

fence2.png 를 땅 구간마다 따로 구워서 그린다. 구멍(pit) 위에는 그리지 않으므로
울타리도 땅과 함께 끊긴다.

구간의 양 끝에는 항상 기둥이 오도록 기둥과 기둥 사이 칸을 나눠 그린다.
"""

import pico2d

# 이미지 아래쪽에서 울타리 아랫단까지의 높이(px). road.png 와 같은 기준이다.
FENCE_BASE = 152
# 원본 이미지를 줄이거나 키우는 비율.
FENCE_SCALE = 1.125
# fence2.png 기둥의 가운데 x 위치(원본 픽셀)와 기둥 반폭.
FENCE_POSTS = (
    15.5, 267.5, 556.0, 843.0, 1092.5, 1344.0, 1633.0, 1919.5, 2171.0,
    2422.5, 2711.0, 2998.0, 3247.5, 3499.5, 3788.0, 4074.5, 4325.5,
)
POST_HALF = 11
BAY_NATIVE = (FENCE_POSTS[-1] - FENCE_POSTS[0]) / (len(FENCE_POSTS) - 1)


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

    def segment(self, art, width):
        """땅 구간 하나만큼의 울타리 텍스처를 돌려준다.

        왼쪽 끝에는 기둥이 오고, 오른쪽 끝에도 기둥이 오도록 칸 수를 정한다.
        """
        fence = self.image
        scale = FENCE_SCALE
        out_w = int(width)
        out_h = int(fence.h * scale)
        post_w = POST_HALF * 2 * scale
        bays = max(1, round((out_w - post_w) / (BAY_NATIVE * scale)))
        bay_w = (out_w - post_w) / bays
        count = len(FENCE_POSTS)

        def paint():
            for j in range(bays):
                i = j % (count - 1)
                src_x0 = FENCE_POSTS[i] - POST_HALF
                src_x1 = FENCE_POSTS[i + 1] - POST_HALF
                pico2d.SDL_RenderCopy(
                    art.renderer, fence.texture,
                    pico2d.SDL_Rect(int(src_x0), 0,
                                    int(src_x1 - src_x0), fence.h),
                    pico2d.SDL_Rect(int(j * bay_w), 0,
                                    int(bay_w) + 1, out_h),
                )
            i = bays % count
            src_x0 = FENCE_POSTS[i] - POST_HALF
            pico2d.SDL_RenderCopy(
                art.renderer, fence.texture,
                pico2d.SDL_Rect(int(src_x0), 0,
                                int(POST_HALF * 2), fence.h),
                pico2d.SDL_Rect(int(out_w - post_w), 0,
                                int(post_w), out_h),
            )

        key = ("fence", out_w, out_h, bays)
        return art.bake(key, out_w, out_h, paint)

    def draw(self, art, width, x, ground_y):
        """구간을 화면 x 에 그린다. 울타리 아랫단이 ground_y 에 오도록 한다."""
        image = self.segment(art, width)
        art.blit_to(image, x, ground_y - FENCE_BASE * FENCE_SCALE,
                    width, image.h)
