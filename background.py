"""배경(도시 실루엣) 그림.

background.png 를 카메라 시차에 따라 가로로 반복해서 그린다.
"""

import pico2d

PARALLAX = 0.2


class Background:
    def __init__(self, path):
        self.path = path
        self._image = None

    @property
    def image(self):
        # 창이 열린 뒤에 불러야 하므로 처음 쓸 때 읽는다.
        if self._image is None:
            self._image = pico2d.load_image(self.path)
        return self._image

    def draw(self, art, camera_x, shake_x=0.0):
        image = self.image
        w = image.w
        h = image.h
        offset = (-camera_x * PARALLAX + shake_x * 0.1) % w
        art.blit_to(image, offset - w, 0, w, h)
        art.blit_to(image, offset, 0, w, h)
