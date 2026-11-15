"""배경(도시 실루엣) 그림.

background.png 를 카메라 시차에 따라 가로로 반복해서 그린다.
같은 크기의 오버레이(background_black.png)를 그 위에 같은 시차로 올린다.
"""

import pico2d

PARALLAX = 0.2


class Background:
    def __init__(self, path, overlay_path=None):
        self.path = path
        self.overlay_path = overlay_path
        self._image = None
        self._overlay = None

    @property
    def image(self):
        # 창이 열린 뒤에 불러야 하므로 처음 쓸 때 읽는다.
        if self._image is None:
            self._image = pico2d.load_image(self.path)
        return self._image

    @property
    def overlay(self):
        if self.overlay_path is None:
            return None
        if self._overlay is None:
            self._overlay = pico2d.load_image(self.overlay_path)
        return self._overlay

    def draw(self, art, camera_x, shake_x=0.0):
        offset = (-camera_x * PARALLAX + shake_x * 0.1)
        self._draw_layer(art, self.image, offset)
        if self.overlay is not None:
            self._draw_layer(art, self.overlay, offset)

    def _draw_layer(self, art, image, offset):
        w = image.w
        h = image.h
        x = offset % w
        art.blit_to(image, x - w, 0, w, h)
        art.blit_to(image, x, 0, w, h)
