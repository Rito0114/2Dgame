"""떠 있는 발판의 그림(상자/벤치).

벤치와 상자는 같은 크기로 그린다. 바닥(도로 윗면)을 기준으로 놓고,
base_offset 으로 그림의 바닥 위치를 조금 옮길 수 있다.
그림의 거의 검은 픽셀(벤치 아래 그림자)은 투명하게 바꾼다.
원본 이미지 파일은 건드리지 않는다.
"""

import ctypes

import pico2d

BLACK_KEY = 20  # 이 값보다 세 채널이 모두 어두운 픽셀은 그림자로 보고 투명하게 한다.
SOURCE_SIZE = 1024  # box.png / bench.png 는 1024x1024 이다.
# 벤치와 상자를 같은 크기로 맞추는 배율.
PROP_SCALE = 0.28


_TEXTURE_CACHE = {}


class Prop:
    def __init__(self, path, bottom_row, base_offset=0, scale=PROP_SCALE,
                 key_shadow=True, contact_y=None):
        # bottom_row: 바닥에 닿는 행(이미지 윗줄 기준)
        # base_offset: 바닥(ground_y)보다 얼마나 더 아래에 놓을지(px, 음수면 아래)
        # scale: 원본 1024px 을 화면 픽셀로 바꾸는 배율
        # key_shadow: 거의 검은 픽셀을 투명하게 바꿀지 여부(그림자 제거)
        # contact_y: 지정하면 바닥 접점을 이 절대 y 에 둔다(base_offset 보다 우선)
        self.path = path
        self.bottom_row = bottom_row
        self.base_offset = base_offset
        self.scale = scale
        self.key_shadow = key_shadow
        self.contact_y = contact_y
        self._texture = None

    def _load(self):
        if self._texture is not None:
            return
        cache_key = (self.path, self.key_shadow)
        if cache_key in _TEXTURE_CACHE:
            self._texture = _TEXTURE_CACHE[cache_key]
            return
        img = pico2d.load_image(self.path)
        w, h = img.w, img.h
        target = pico2d.SDL_CreateTexture(
            pico2d.pico2d.renderer, pico2d.SDL_PIXELFORMAT_ABGR8888,
            pico2d.SDL_TEXTUREACCESS_TARGET, w, h)
        pico2d.SDL_SetRenderTarget(pico2d.pico2d.renderer, target)
        pico2d.SDL_SetRenderDrawColor(pico2d.pico2d.renderer, 0, 0, 0, 0)
        pico2d.SDL_RenderClear(pico2d.pico2d.renderer)
        pico2d.SDL_SetTextureBlendMode(img.texture, pico2d.SDL_BLENDMODE_NONE)
        pico2d.SDL_RenderCopy(pico2d.pico2d.renderer, img.texture, None,
                              pico2d.SDL_Rect(0, 0, w, h))
        buf = (ctypes.c_ubyte * (w * h * 4))()
        pico2d.SDL_RenderReadPixels(pico2d.pico2d.renderer, None,
                                    pico2d.SDL_PIXELFORMAT_ABGR8888, buf,
                                    w * 4)
        pico2d.SDL_SetRenderTarget(pico2d.pico2d.renderer, None)
        pico2d.SDL_DestroyTexture(target)

        pixels = bytearray(buf)
        if self.key_shadow:
            for i in range(0, len(pixels), 4):
                if pixels[i + 3] and (pixels[i] < BLACK_KEY
                                      and pixels[i + 1] < BLACK_KEY
                                      and pixels[i + 2] < BLACK_KEY):
                    pixels[i + 3] = 0

        texture = pico2d.SDL_CreateTexture(
            pico2d.pico2d.renderer, pico2d.SDL_PIXELFORMAT_ABGR8888,
            pico2d.SDL_TEXTUREACCESS_STATIC, w, h)
        raw = (ctypes.c_ubyte * len(pixels)).from_buffer(pixels)
        pico2d.SDL_UpdateTexture(texture, None, raw, w * 4)
        pico2d.SDL_SetTextureBlendMode(texture, pico2d.SDL_BLENDMODE_BLEND)
        self._texture = texture
        _TEXTURE_CACHE[cache_key] = texture

    def base_y(self, ground_y):
        """바닥 접점의 y(캔버스 좌표)."""
        if self.contact_y is not None:
            return self.contact_y
        return ground_y + self.base_offset

    def row_y(self, row, ground_y):
        """원본 이미지의 행 row 가 화면에서 놓이는 y."""
        return self.base_y(ground_y) + (self.bottom_row - row) * self.scale

    def size(self):
        return SOURCE_SIZE * self.scale

    def draw(self, art, center_x, ground_y):
        """center_x 에 놓고, 바닥 기준으로 같은 크기로 그린다."""
        self._load()
        size = int(round(SOURCE_SIZE * self.scale))
        if self.contact_y is not None:
            base = self.contact_y
        else:
            base = ground_y + self.base_offset
        bottom = base - (SOURCE_SIZE - self.bottom_row) * self.scale
        texture = self._texture

        def paint():
            pico2d.SDL_RenderCopy(
                art.renderer, texture, None,
                pico2d.SDL_Rect(0, 0, size, size),
            )

        image = art.bake(("prop", self.path, size, base, self.scale),
                         size, size, paint)
        art.blit_to(image, center_x - size * 0.5, bottom, size, size)
