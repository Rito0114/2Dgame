"""코인과 회복 아이템(포션)의 데이터와 그림.

- Coin: 줄을 먹으면 점수가 오르는 코인. 그림은 sprites/object/coin.png.
- HeartPickup: 먹으면 체력을 채우는 회복 아이템. 그림은 sprites/object/potion.png.
"""

import math
import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECT_DIR = os.path.join(BASE_DIR, "sprites", "object")
COIN_FILE = os.path.join(OBJECT_DIR, "coin.png")
POTION_FILE = os.path.join(OBJECT_DIR, "potion.png")
COIN_SIZE = 52  # 코인 그림 한 변(px)
POTION_SIZE = 56  # 포션 그림 한 변(px)
SCREEN_W = 1280  # 화면 가로(px). 화면 밖의 아이템은 그리지 않는다.

_images = {}


def _image(path):
    """아이템 그림을 처음 쓸 때 한 번만 읽는다(창이 열린 뒤에 읽어야 한다)."""
    if path not in _images:
        _images[path] = pico2d.load_image(path)
    return _images[path]


def coin_image():
    return _image(COIN_FILE)


def heart_pickup_image():
    return _image(POTION_FILE)


class Coin:
    __slots__ = ("x", "y", "phase", "taken")

    def __init__(self, x, y, phase):
        self.x = x
        self.y = y
        self.phase = phase
        self.taken = False

    def draw(self, art, camera_x, time, shake_x=0.0):
        if self.taken:
            return
        x = self.x - camera_x + shake_x
        if x < -30 or x > SCREEN_W + 30:
            return
        y = self.y + math.sin(time * 4.0 + self.phase) * 5
        art.blit(coin_image(), x, y, COIN_SIZE, COIN_SIZE)


class HeartPickup:
    __slots__ = ("x", "y", "phase", "taken")

    def __init__(self, x, y, phase):
        self.x = x
        self.y = y
        self.phase = phase
        self.taken = False

    def draw(self, art, camera_x, time, shake_x=0.0):
        if self.taken:
            return
        x = self.x - camera_x + shake_x
        if x < -40 or x > SCREEN_W + 40:
            return
        y = self.y + math.sin(time * 3.0 + self.phase) * 6
        art.blit(heart_pickup_image(), x, y, POTION_SIZE, POTION_SIZE)

