"""화면 UI 오버레이: UI 배경, 목숨(hp), 스킬 쿨타임.

- UI_background.png: UI 배경. 왼쪽 아래에 그려진다.
- hp_N.png: 잃은 목숨의 수만큼 켠다.
  목숨이 전부 있으면 아무것도 켜지지 않고, 하나 잃으면 hp_1, 둘 잃으면 hp_1 과 hp_2 를 켠다.
  회복 아이템으로 목숨이 하나 늘면 가장 마지막에 켜진 hp 그림이 꺼진다.
- skill_time.png: 스킬을 쓰면 나타나고, 쿨타임이 줄면 아래에서 위로 사라진다.

모든 UI 그림은 화면 전체 크기 기준이며, UI_SCALE 로 줄여서 왼쪽 아래 모서리에 맞춘다.
"""

import os

import pico2d

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_DIR = os.path.join(BASE_DIR, "sprites", "UI")
BACKGROUND_FILE = os.path.join(UI_DIR, "UI_background.png")
HP_FILE = os.path.join(UI_DIR, "hp_{}.png")
SKILL_TIME_FILE = os.path.join(UI_DIR, "skill_time.png")
KILL_ICON_FILE = os.path.join(UI_DIR, "killcounter.png")
MAX_HP = 5
UI_SCALE = 0.75  # UI 그림의 화면 배율(원래 크기 대비)

# skill_time.png 에서 회색 원이 차지하는 세로 범위(원본 1080 기준, 위쪽이 0)
SKILL_DISC_TOP = 918
SKILL_DISC_BOTTOM = 1060
SKILL_SRC_H = 1080

_images = {}


def _image(path):
    """UI 그림을 처음 쓸 때 한 번만 읽는다(창이 열린 뒤에 읽어야 한다)."""
    if path not in _images:
        _images[path] = pico2d.load_image(path)
    return _images[path]


def kill_icon():
    return _image(KILL_ICON_FILE)


class HUDOverlay:
    def draw(self, art, width, height, hp, cooldown_ratio=0.0):
        ui_w = width * UI_SCALE
        ui_h = height * UI_SCALE
        art.blit_to(_image(BACKGROUND_FILE), 0, 0, ui_w, ui_h)
        lost = max(0, min(MAX_HP, MAX_HP - hp))
        for k in range(1, lost + 1):
            art.blit_to(_image(HP_FILE.format(k)), 0, 0, ui_w, ui_h)
        self._draw_skill_time(art, width, height, cooldown_ratio)

    def _draw_skill_time(self, art, width, height, cooldown_ratio):
        """스킬을 쓰면 나타나고, 쿨타임이 줄면 원이 아래에서 위로 사라진다(cooldown_ratio 0~1, 0이면 안 그림)."""
        ratio = max(0.0, min(1.0, cooldown_ratio))
        if ratio <= 0.0:
            return
        image = _image(SKILL_TIME_FILE)
        ui_w = width * UI_SCALE
        ui_h = height * UI_SCALE
        # 원 윗부분은 남기고, 아래쪽부터 잘라낸다.
        cut = int(SKILL_DISC_TOP + (SKILL_DISC_BOTTOM - SKILL_DISC_TOP) * ratio)
        scale = ui_h / SKILL_SRC_H
        top = height - ui_h  # 그림 윗변의 화면 y(SDL 좌표, 위에서 아래로)
        src = pico2d.SDL_Rect(0, 0, image.w, cut)
        dst = pico2d.SDL_Rect(0, int(top), int(ui_w), int(cut * scale))
        pico2d.SDL_RenderCopy(art.renderer, image.texture, src, dst)
