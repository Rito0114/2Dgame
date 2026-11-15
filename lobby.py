"""로비 화면(처음 나오는 시작 화면).

무대 위에 주인공이 서 있고, 제목과 조작법, 최고 점수를 보여준다.
SPACE 를 누르면 게임이 시작된다. 그리기만 담당하며, 키 처리는 main.py 에서 한다.
"""

import math

import pico2d


class Lobby:
    def __init__(self, width, height, ground_y, stand_y):
        self.width = width
        self.height = height
        self.ground_y = ground_y
        self.stand_y = stand_y
        self._spotlight = None
        self._glow = None

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

        frame = int(game.time / 0.13)
        game.girl.draw_preview(986, self.stand_y + 8, 0.62, frame)

        title_x = 430
        a.blit(self._glow_image(a), title_x, 500)
        game.text.draw(72, title_x, 520, "그림자 소녀",
                       (246, 242, 255), "center", shadow=(52, 20, 80))
        game.text.draw(22, title_x, 462, "S H A D O W   G I R L",
                       (140, 230, 230), "center")
        game.text.draw(19, title_x, 420,
                       "어둠이 삼킨 숲을 지나 빛의 문으로",
                       (170, 170, 215), "center")

        blink = abs(math.sin(game.time * 2.2))
        if blink > 0.25:
            game.text.draw(28, title_x, 330,
                           "SPACE 키를 눌러 시작",
                           (255, 236, 190), "center")

        game.text.draw(18, 60, 250,
                       "A / D  또는  ← / →    이동", (200, 210, 235))
        game.text.draw(18, 60, 218,
                       "SPACE / W / ↑         점프", (200, 210, 235))
        game.text.draw(18, 60, 186,
                       "J / X                 공격", (200, 210, 235))
        game.text.draw(18, 60, 154,
                       "P                     일시정지", (150, 160, 190))
        if game.best_score > 0:
            game.text.draw(18, self.width - 60, 40,
                           "BEST %06d" % game.best_score,
                           (220, 210, 160), align="right")
        game._draw_fps(self.width - 24, 26, align="right")
        if game.renderer_name:
            game.text.draw(14, self.width - 24, 8,
                           "renderer: %s" % game.renderer_name,
                           (110, 120, 150), align="right", shadow=None)
