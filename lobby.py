"""로비 화면(처음 나오는 시작 화면).

무대 위에 주인공이 서 있고, 제목과 조작법, 최고 점수를 보여준다.
SPACE 를 누르면 게임이 시작된다. 그리기만 담당하며, 키 처리는 main.py 에서 한다.
"""

import math
import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_FILE = os.path.join(BASE_DIR, "sprites", "UI", "logo.png")
LOGO_WIDTH = 960  # 로고 가로 길이(px). 이전의 2배.
LOGO_CENTER_Y = 400
PROMPT_Y = 200


class Lobby:
    def __init__(self, width, height, ground_y, stand_y):
        self.width = width
        self.height = height
        self.ground_y = ground_y
        self.stand_y = stand_y
        self._spotlight = None
        self._glow = None
        self._logo = None

    def _logo_image(self):
        if self._logo is None:
            self._logo = pico2d.load_image(LOGO_FILE)
        return self._logo

    def _spotlight_image(self, a):
        if self._spotlight is None:
            def paint():
                pico2d.draw_circle(240, 240, 240, 255, 210, 160, 14, filled=True)
                pico2d.draw_circle(240, 240, 180, 255, 210, 160, 20, filled=True)
                pico2d.draw_circle(240, 240, 120, 255, 210, 160, 26, filled=True)

            self._spotlight = a.bake("spotlight", 480, 480, paint)
        return self._spotlight

    def _glow_image(self, a):
        if self._glow is None:
            def paint():
                pico2d.draw_circle(300, 300, 300, 120, 80, 200, 20, filled=True)
                pico2d.draw_circle(300, 300, 220, 120, 80, 200, 18, filled=True)

            self._glow = a.bake("title_glow", 600, 600, paint)
        return self._glow

    def draw(self, game, a):
        """로비 화면을 그린다. game 은 시간, 글자, 바닥, 주인공, 최고 점수를 제공한다."""
        # 무대 (플레이 화면과 같은 바닥 그림)
        pico2d.draw_rectangle(0, 0, self.width, self.ground_y, 18, 24, 46, filled=True)
        game.world.road.draw_top(a, 0, self.ground_y)

        # 스포트라이트
        a.blit(self._spotlight_image(a), 986, self.ground_y + 200)

        center_x = self.width * 0.5
        a.blit(self._glow_image(a), center_x, LOGO_CENTER_Y)
        logo = self._logo_image()
        logo_height = LOGO_WIDTH * logo.h / logo.w
        a.blit(logo, center_x, LOGO_CENTER_Y, LOGO_WIDTH, logo_height)

        blink = abs(math.sin(game.time * 2.2))
        if blink > 0.25:
            game.text.draw(28, center_x, PROMPT_Y,
                           "SPACE 키를 눌러 시작",
                           (255, 236, 190), "center")

        if game.best_score > 0:
            game.text.draw(18, self.width - 60, 40,
                           "BEST %06d" % game.best_score,
                           (220, 210, 160), align="right")
        game._draw_fps(self.width - 24, 26, align="right")
        if game.renderer_name:
            game.text.draw(14, self.width - 24, 8,
                           "renderer: %s" % game.renderer_name,
                           (110, 120, 150), align="right", shadow=None)
