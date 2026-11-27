"""보스 스테이지 배경 장식.

- 부서진 벽(broken_wall.png): 맵 오른쪽 끝 배경
- 기둥(pillar.png) 4개: 맵 전체에 균등하게 배치

두 그림 모두 실제 그림의 가장 아래쪽이 도로 윗면(GROUND)에 닿도록 하고,
기둥은 가장 위쪽이 화면 위로 넘어가도록 크기를 맞춘다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OBJECT_DIR = os.path.join(BASE_DIR, "sprites", "object")
BROKEN_WALL_FILE = os.path.join(OBJECT_DIR, "broken_wall.png")
PILLAR_FILE = os.path.join(OBJECT_DIR, "pillar.png")

# 원본 PNG에서 실제 그림이 차지하는 영역(좌상단 기준, 투명 여백 제외)
# broken_wall: 1920x1080 / pillar: 1920x1080
WALL_BOX = (723, 133, 1867, 898)
PILLAR_BOX = (694, 28, 1241, 1043)

BROKEN_WALL_SCALE = 0.6  # 벽의 위쪽은 화면 안에 들어오게
PILLAR_SCALE = 0.65  # 기둥 위쪽이 화면(720px) 위로 나가게
PILLAR_COUNT = 4
PILLAR_CONTENT_W = (PILLAR_BOX[2] - PILLAR_BOX[0]) * PILLAR_SCALE
PILLAR_CONTENT_HALF = PILLAR_CONTENT_W * 0.5
WALL_RIGHT_MARGIN = 100  # 맵 오른쪽 끝에서 벽 중심까지의 거리


class BossScenery:
    """보스 스테이지 전용 배경 장식 그리기."""

    def __init__(self, world_w, ground_y):
        self.world_w = world_w
        self.ground_y = ground_y
        self.hidden_pillars = set()  # 상자 뒤에 가려진 기둥 번호
        self._wall = None
        self._pillar = None

    @property
    def wall(self):
        # 창이 열린 뒤에 불러야 하므로 처음 쓸 때 읽는다.
        if self._wall is None:
            self._wall = pico2d.load_image(BROKEN_WALL_FILE)
        return self._wall

    @property
    def pillar(self):
        if self._pillar is None:
            self._pillar = pico2d.load_image(PILLAR_FILE)
        return self._pillar

    def hide_pillars_behind(self, furniture):
        """상자('high')가 앞에 놓인 기둥은 그리지 않고 판정에서도 제외한다."""
        self.hidden_pillars = set()
        step = self.world_w / PILLAR_COUNT
        for kind, prop, cx in furniture:
            if kind != "high":
                continue
            half = prop.size() * 0.5
            for i in range(PILLAR_COUNT):
                pillar_x = step * (i + 0.5)
                if abs(cx - pillar_x) <= PILLAR_CONTENT_HALF + half:
                    self.hidden_pillars.add(i)

    def pillar_at(self, x, half_w=0.0):
        """월드 x 가 보이는 기둥 그림 범위에 있으면 기둥 번호를, 없으면 None."""
        step = self.world_w / PILLAR_COUNT
        for i in range(PILLAR_COUNT):
            if i in self.hidden_pillars:
                continue
            cx = step * (i + 0.5)
            if abs(x - cx) <= PILLAR_CONTENT_HALF + half_w:
                return i
        return None

    def draw(self, art, camera_x, shake_x=0.0):
        self._draw(art, self.wall, self.world_w - WALL_RIGHT_MARGIN,
                   BROKEN_WALL_SCALE, WALL_BOX, camera_x, shake_x)

        step = self.world_w / PILLAR_COUNT
        for i in range(PILLAR_COUNT):
            if i in self.hidden_pillars:
                continue
            self._draw(art, self.pillar, step * (i + 0.5),
                       PILLAR_SCALE, PILLAR_BOX, camera_x, shake_x)

    def _draw(self, art, image, world_x, scale, box, camera_x, shake_x):
        """그림의 가운데를 world_x, 실제 아래쪽을 ground_y 에 맞춰 그린다."""
        left, _top, right, bottom = box
        content_center = (left + right) * 0.5 * scale
        image_bottom = self.ground_y - (image.h - bottom) * scale
        screen_left = world_x - camera_x + shake_x - content_center
        art.blit_to(image, screen_left, image_bottom,
                    image.w * scale, image.h * scale)
