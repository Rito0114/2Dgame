"""체크포인트 가로등 그림.

도달 전에는 lamp_off.png, 체크포인트가 활성화되면 lamp_on.png 를 그린다.
가로등 기둥의 가운데가 체크포인트 x 에 오고, 아랫면이 지면(ground_y)에 닿는다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OFF_FILE = os.path.join(BASE_DIR, "sprites", "object", "lamp_off.png")
ON_FILE = os.path.join(BASE_DIR, "sprites", "object", "lamp_on.png")

SCALE = 0.21  # 원본 1024x1536 을 화면 크기로 줄이는 배율
POLE_X = 654  # 기둥 가운데의 원본 x
BASE_PAD = 32  # 아랫면에서 이미지 아래 가장자리까지의 원본 px
DROP = 10  # 지면보다 아래로 내리는 양(px)


class Lamp:
    def __init__(self, off_path=OFF_FILE, on_path=ON_FILE):
        self.off_path = off_path
        self.on_path = on_path
        self._off = None
        self._on = None

    def _images(self):
        # 창이 열린 뒤에 불러야 하므로 처음 쓸 때 읽는다.
        if self._off is None:
            self._off = pico2d.load_image(self.off_path)
            self._on = pico2d.load_image(self.on_path)
        return self._off, self._on

    def draw(self, art, x, ground_y, active):
        off, on = self._images()
        image = on if active else off
        width = image.w * SCALE
        height = image.h * SCALE
        left = x - POLE_X * SCALE
        bottom = ground_y - BASE_PAD * SCALE - DROP
        art.blit_to(image, left, bottom, width, height)
