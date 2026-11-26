"""그림자 소녀 — 플레이어 캐릭터 클래스.

`main.py` 와 분리해서 캐릭터의 상태 머신(대기/달리기/점프/공격/피격/사망)과
물리, 충돌, 애니메이션을 모두 이 파일에서 관리한다.

스프라이트 시트는 모두 1536x1024 이고 5열 x 2행(총 10프레임)으로 구성되어 있다.
"""

import math
import os

import pico2d
import sdl2

from dash import DURATION as DASH_DURATION
from dash import LAST_FRAME_ELAPSED, draw_dash, lead_offset

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 스프라이트 시트 정보 -------------------------------------------------
SHEET_FILES = {
    "idle": os.path.join("sprites", "girl", "idle_sprite.png"),
    "idle2": os.path.join("sprites", "girl", "idle_sprite2.png"),
    "jump": os.path.join("sprites", "girl", "jump_sprite.png"),
    "attack": os.path.join("sprites", "girl", "attack_sprite2.png"),
    "hit": os.path.join("sprites", "girl", "hit_sprite.png"),
    "retire": os.path.join("sprites", "girl", "retire_sprite2.png"),
    "run": os.path.join("sprites", "girl", "run_sprite4.png"),
}
# 시트별 (열 수, 행 수). 대부분 5x2 이고, 달리기는 20프레임(5x4)이다.
SHEET_GRID = {
    "idle": (5, 2),
    "idle2": (5, 1),
    "jump": (5, 2),
    "attack": (5, 2),
    "hit": (5, 2),
    "retire": (5, 2),
    "run": (5, 4),
}

# 화면에 그릴 때 크기(원본 307x512 셀을 0.38배로 축소)
SCALE = 0.38
# 달리기 시트는 머리가 상대적으로 커서, 화면에서 머리 폭이 대기 자세와 같도록 줄인다.
SHEET_SCALE = {"run": 0.531, "idle2": 0.46, "attack": 0.48, "retire": 0.44}
# 공격(attack_sprite2.png, 5x2) 프레임마다 발바닥이 셀 아래쪽에서 떨어진 높이(원본 px)
ATTACK2_PAD = (29, 31, 32, 32, 32, 43, 43, 41, 40, 40)
# 대기 애니메이션(idle_sprite2.png, 5프레임)은 1 2 3 4 5 4 3 2 를 무한 반복한다.
IDLE2_CYCLE = (0, 1, 2, 3, 4, 3, 2, 1)
# 프레임마다 발바닥이 셀 아래쪽에서 떨어진 높이(원본 px)
IDLE2_PAD = (18, 20, 23, 25, 27)
# 프레임마다 캐릭터 가로 중심(셀 안 x, 원본 px). 중심축이 흔들리지 않도록 맞춘다.
IDLE2_CENTER_X = (94.5, 102.5, 113.5, 120.5, 127.5)
IDLE2_CELL_CENTER = 113.5

# 시트마다 셀 아래쪽 여백(캐릭터 발이 셀 바닥에서 얼마나 떨어져 있는지)이 다르다.
# 실측값(px, 원본 기준)을 시트별로 보정해서 시트를 바꿔도 발 높이가 크게 튀지 않게 한다.
FOOT_PAD = {
    "idle": 42,
    "jump": 44,
    "attack": 36,
    "hit": 40,
    "retire": 48,
}
# 사망 모션은 몸이 바닥으로 내려앉는 동작이라, 프레임마다 가장 낮은 픽셀이
# 정확히 발밑 좌표에 오도록 맞춰야 땅에 뜨거나 파묻히지 않는다.
# retire_sprite2.png(5x2, 셀 250x400): 프레임마다 발바닥이 셀 아래쪽에서 떨어진 높이(원본 px)
RETIRE2_PAD = (29, 29, 32, 26, 26, 56, 57, 56, 54, 51)
# 달리기 프레임마다 발바닥이 셀 아래쪽에서 떨어진 높이(원본 px). 발이 땅에 붙도록 보정한다.
RUN_PAD = (9, 13, 8, 8, 8, 11, 10, 9, 9, 8, 9, 13, 8, 8, 8, 12, 11, 10, 10, 9)

LEFT_KEYS = {sdl2.SDLK_LEFT}
RIGHT_KEYS = {sdl2.SDLK_RIGHT}
JUMP_KEYS = {sdl2.SDLK_SPACE}
DROP_KEYS = {sdl2.SDLK_DOWN}
ATTACK_KEYS = {sdl2.SDLK_j, sdl2.SDLK_x, sdl2.SDLK_k, sdl2.SDLK_LCTRL}
DASH_KEYS = {sdl2.SDLK_q}

_sheet_cache = {}


def _sheet(name):
    if name not in _sheet_cache:
        path = os.path.join(BASE_DIR, SHEET_FILES[name])
        _sheet_cache[name] = pico2d.load_image(path)
    return _sheet_cache[name]


def _cell_rect(name, frame):
    """시트 name 의 프레임 번호에 해당하는 (left, bottom, width, height)를 돌려준다."""
    sheet = _sheet(name)
    cols, rows = SHEET_GRID[name]
    col = frame % cols
    row = frame // cols
    left = int(round(col * sheet.w / cols))
    right = int(round((col + 1) * sheet.w / cols))
    top = int(round(row * sheet.h / rows))
    bottom_row = int(round((row + 1) * sheet.h / rows))
    return left, sheet.h - bottom_row, right - left, bottom_row - top


def idle2_shift(frame, scale, facing):
    """대기 프레임의 중심 차이를 상쇄하는 가로 이동량(화면 px)."""
    rel = IDLE2_CENTER_X[frame] - IDLE2_CELL_CENTER
    return -rel * scale * (-1.0 if facing < 0 else 1.0)


class Girl:
    """횡스크롤 액션 플랫포머의 주인공."""

    MAX_HP = 5
    HITBOX_W = 46
    HITBOX_H = 150

    SPEED = 360.0
    ACCEL = 3400.0
    FRICTION = 3200.0
    GRAVITY = 2300.0
    JUMP_V = 880.0
    DROP_SPEED = 260.0  # 아래 점프를 시작할 때 주는 하강 속도
    DASH_SPEED = 900.0  # 대쉬 속도
    DASH_TIME = DASH_DURATION  # 대쉬 지속 시간(잔상 프레임 17개와 같다)
    DASH_END_BACK = 200.0  # 대쉬가 끝난 뒤 마지막 위치에서 왼쪽으로 옮기는 거리(px)
    DASH_INVULN_TIME = 3.0  # 대쉬가 끝난 뒤 무적 시간(초). 반투명으로 표시한다.
    DASH_COOLDOWN = 40.0  # 대쉬 재사용 대기 시간(초)
    MAX_FALL = 1400.0
    COYOTE = 0.10
    JUMP_BUFFER = 0.14
    ATTACK_TIME = 0.55
    HIT_TIME = 0.36

    def __init__(self, x, y):
        # 위치(y 는 발밑 좌표)와 속도
        self.x = float(x)
        self.y = float(y)
        # 시작 높이를 지면 높이로 기억해 둔다(스킬 중 지면 아래로 내려가지 않게 하는 기준).
        self.ground_y = float(y)
        self.prev_y = self.y
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1

        # 상태
        self.state = "idle"
        self.anim_time = 0.0
        self.hp = self.MAX_HP
        self.on_ground = True
        self.coyote = self.COYOTE
        self.jump_buffer = 0.0
        self.jump_held = False
        self.jump_cut = False
        self.invuln = 0.0
        self.hit_stun = 0.0
        self.attack_timer = 0.0
        self.attack_elapsed = 0.0
        self.attack_id = 0
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_invuln = 0.0
        # 대쉬 스킬 해금 여부. 1스테이지에서는 잠겨 있다(스테이지가 정한다).
        self.dash_unlocked = True
        # 개발자 메뉴 옵션(무적, 스킬 쿨타임 0초).
        self.dev_invincible = False
        self.dev_no_cooldown = False

        # 이벤트(먼지/사운드용)
        self.just_jumped = False
        self.just_landed = False
        self.land_speed = 0.0

        self.keys = set()
        # 아래 점프: 단방향 발판을 아래로 통과해 떨어진다.
        self.floor = None  # 지금 서 있는 발판
        self.drop_request = False
        self.drop_through = None  # 통과 중인 단방향 발판
        self.limit_left = -1e9
        self.limit_right = 1e9

    # ------------------------------------------------------------------
    # 입력
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type == sdl2.SDL_KEYDOWN:
            key = event.key
            if key in LEFT_KEYS:
                self.keys.add("left")
            elif key in RIGHT_KEYS:
                self.keys.add("right")
            elif key in DROP_KEYS:
                self.keys.add("down")
            elif key in JUMP_KEYS:
                self.jump_held = True
                self.jump_buffer = self.JUMP_BUFFER
                # 아래 화살표를 누른 채 스페이스를 누르면 단방향 발판을 통과해 떨어진다.
                if "down" in self.keys:
                    self.drop_request = True
            elif key in DASH_KEYS:
                return self.request_dash()
            elif key in ATTACK_KEYS:
                self.request_attack()
        elif event.type == sdl2.SDL_KEYUP:
            key = event.key
            if key in LEFT_KEYS:
                self.keys.discard("left")
            elif key in RIGHT_KEYS:
                self.keys.discard("right")
            elif key in DROP_KEYS:
                self.keys.discard("down")
            elif key in JUMP_KEYS:
                self.jump_held = False

    def clear_keys(self):
        self.keys.clear()
        self.jump_held = False
        self.drop_request = False

    def request_attack(self):
        if self.state in ("retire", "hit") or self.hit_stun > 0:
            return
        if self.attack_timer > 0:
            return
        self.attack_timer = self.ATTACK_TIME
        self.attack_elapsed = 0.0
        self.attack_id += 1

    def request_dash(self):
        """대쉬를 시작하면 True 를 돌려준다."""
        if not self.dash_unlocked:
            return False
        if self.state in ("retire", "hit") or self.hit_stun > 0:
            return False
        if self.dash_timer > 0 or (self.dash_cooldown > 0
                                   and not self.dev_no_cooldown):
            return False
        self.dash_timer = self.DASH_TIME
        self.dash_cooldown = (0.0 if self.dev_no_cooldown
                              else self.DASH_COOLDOWN)
        self.attack_timer = 0.0
        self.anim_time = 0.0
        return True

    def request_jump(self):
        if self.state == "retire":
            return
        self.jump_buffer = self.JUMP_BUFFER

    # ------------------------------------------------------------------
    # 충돌 / 상태
    # ------------------------------------------------------------------
    @property
    def left(self):
        return self.x - self.HITBOX_W * 0.5

    @property
    def right(self):
        return self.x + self.HITBOX_W * 0.5

    @property
    def bottom(self):
        return self.y

    @property
    def top(self):
        return self.y + self.HITBOX_H

    def focus_x(self):
        """카메라와 피격 판정의 기준 x. 대쉬 중에는 가장 오른쪽(앞쪽) 픽셀이다."""
        if self.dash_timer > 0.0:
            return self.x + lead_offset(self.anim_time, self.facing)
        return self.x

    def rect(self):
        return (self.focus_x() - self.HITBOX_W * 0.5, self.bottom,
                self.HITBOX_W, self.HITBOX_H)

    def _overlaps(self, platform):
        return (
            self.left < platform.right
            and self.right > platform.left
            and self.bottom < platform.top
            and self.top > platform.bottom
        )

    def attack_hitbox(self):
        """공격 판정이 켜져 있는 동안의 (left, bottom, width, height)."""
        if self.state != "attack":
            return None
        if not (0.10 <= self.attack_elapsed <= 0.34):
            return None
        center = self.x + self.facing * 62
        return center - 54, self.y + 18, 108, 118

    def bounce(self, power=680.0):
        self.vy = power
        self.on_ground = False
        self.jump_cut = True
        self._set_state("jump")

    def take_hit(self, source_x):
        # 대쉬 중에는 무적이다.
        if (self.dev_invincible or self.state == "retire" or self.invuln > 0
                or self.dash_timer > 0 or self.dash_invuln > 0):
            return False
        self.hp -= 1
        self.invuln = 1.25
        self.hit_stun = self.HIT_TIME
        self.attack_timer = 0.0
        self.dash_timer = 0.0
        self.attack_elapsed = 0.0
        self.on_ground = False
        self.jump_buffer = 0.0
        self.jump_held = False
        # 공격자 쪽을 바라보되, 넉백은 반대 방향(뒤로)으로 밀린다.
        self.facing = 1 if source_x >= self.x else -1
        self.vx = -330.0 * self.facing
        self.vy = 420.0
        self._set_state("hit")
        if self.hp <= 0:
            self.die()
        return True

    def die(self):
        self.hp = 0
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.attack_timer = 0.0
        self.hit_stun = 0.0
        self.dash_timer = 0.0
        self.anim_time = 0.0
        self.state = "retire"

    def heal(self, amount=1):
        self.hp = min(self.MAX_HP, self.hp + amount)

    def respawn(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.prev_y = self.y
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = True
        self.coyote = self.COYOTE
        self.invuln = 1.6
        self.hit_stun = 0.0
        self.attack_timer = 0.0
        self.dash_timer = 0.0
        self.jump_buffer = 0.0
        self.jump_held = False
        self.anim_time = 0.0
        self.state = "idle"

    @property
    def retire_done(self):
        return self.state == "retire" and self.anim_time > 1.45

    # ------------------------------------------------------------------
    # 업데이트
    # ------------------------------------------------------------------
    def update(self, dt, platforms):
        self.just_jumped = False
        self.just_landed = False
        self.prev_y = self.y

        if self.state == "retire":
            # 쓰러지는 동안에도 중력은 적용해서, 공중에서 죽어도 땅으로 내려앉는다.
            self.anim_time += dt
            if not self.on_ground:
                self.vy = max(self.vy - self.GRAVITY * dt, -self.MAX_FALL)
                prev_bottom = self.y
                self.y += self.vy * dt
                for platform in platforms:
                    if self.right <= platform.left or self.left >= platform.right:
                        continue
                    if (prev_bottom >= platform.top - 0.5
                            and self.y <= platform.top):
                        self.y = platform.top
                        self.vy = 0.0
                        self.on_ground = True
                        break
                if self.y < -400.0:  # 구멍으로 떨어져 내려가는 경우
                    self.y = -400.0
                    self.vy = 0.0
            return

        dt = min(dt, 1.0 / 30.0)

        self.invuln = max(0.0, self.invuln - dt)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.hit_stun = max(0.0, self.hit_stun - dt)
        was_dashing = self.dash_timer > 0.0
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.dash_invuln = max(0.0, self.dash_invuln - dt)
        if was_dashing and self.dash_timer <= 0.0:
            # 대쉬가 끝나면 마지막 프레임의 가장 오른쪽 픽셀 위치로 옮겨 놓는다.
            self.x += lead_offset(LAST_FRAME_ELAPSED, self.facing) - self.DASH_END_BACK * self.facing
            self.dash_invuln = self.DASH_INVULN_TIME
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        attacking = self.attack_timer > 0.0
        if attacking:
            self.attack_timer -= dt
            self.attack_elapsed += dt
            if self.attack_timer <= 0.0:
                self.attack_timer = 0.0
                attacking = False

        # --- 좌우 이동 -------------------------------------------------
        direction = 0
        if "left" in self.keys and "right" not in self.keys:
            direction = -1
        elif "right" in self.keys and "left" not in self.keys:
            direction = 1

        if self.dash_timer > 0.0:
            self.vx = self.facing * self.DASH_SPEED
        elif self.hit_stun > 0.0:
            self.vx = self._approach(self.vx, 0.0, 1800.0 * dt)
        else:
            if direction:
                self.facing = direction
            control = 0.55 if attacking else 1.0
            target = direction * self.SPEED * control
            accel = self.ACCEL if direction else self.FRICTION
            self.vx = self._approach(self.vx, target, accel * dt)

        # --- 아래 점프 -------------------------------------------------
        if self.drop_request:
            self.drop_request = False
            if (self.on_ground and self.hit_stun <= 0.0
                    and self.floor is not None and self.floor.one_way):
                self.drop_through = self.floor
                self.vy = -self.DROP_SPEED
                self.on_ground = False
                self.coyote = 0.0
                self.jump_buffer = 0.0
                self.floor = None

        # --- 점프 ------------------------------------------------------
        if self.on_ground:
            self.coyote = self.COYOTE
        else:
            self.coyote = max(0.0, self.coyote - dt)

        if self.hit_stun <= 0.0 and self.jump_buffer > 0.0 and self.coyote > 0.0:
            self.vy = self.JUMP_V
            self.on_ground = False
            self.coyote = 0.0
            self.jump_buffer = 0.0
            self.jump_cut = False
            self.just_jumped = True

        # 점프 키를 짧게 누르면 낮게 뛴다.
        if not self.jump_held and self.vy > 0.0 and not self.jump_cut:
            self.vy *= 0.45
            self.jump_cut = True

        # --- 중력 ------------------------------------------------------
        self.vy = max(self.vy - self.GRAVITY * dt, -self.MAX_FALL)

        # --- X 이동 및 벽 충돌 -----------------------------------------
        self.x += self.vx * dt
        for platform in platforms:
            if platform.one_way:
                continue
            if not self._overlaps(platform):
                continue
            if self.vx > 0.0:
                self.x = platform.left - self.HITBOX_W * 0.5
            elif self.vx < 0.0:
                self.x = platform.right + self.HITBOX_W * 0.5
            else:
                continue
            self.vx = 0.0

        # --- Y 이동 및 바닥/천장 충돌 ----------------------------------
        # 빠르게 떨어질 때 얇은 발판을 통과하지 않도록, 이전 위치에서 현재
        # 위치까지의 이동 구간으로 충돌을 검사한다. 단방향 발판은 위에서만
        # 착지하고, 아래에서 올라갈 때는 그대로 통과한다.
        fall_speed = self.vy
        prev_bottom = self.y
        self.y += self.vy * dt
        was_on_ground = self.on_ground
        self.on_ground = False
        self.floor = None

        for platform in platforms:
            if platform is self.drop_through:
                continue
            if self.right <= platform.left or self.left >= platform.right:
                continue
            if self.vy <= 0.0:
                landed = (
                    prev_bottom >= platform.top - 0.5
                    and self.y <= platform.top
                )
                if landed or (not platform.one_way and self._overlaps(platform)):
                    self.y = platform.top
                    self.vy = 0.0
                    self.on_ground = True
                    self.floor = platform
                    if not was_on_ground and fall_speed < -240.0:
                        self.just_landed = True
                        self.land_speed = -fall_speed
                    break
            elif not platform.one_way and self._overlaps(platform):
                self.y = platform.bottom - self.HITBOX_H
                self.vy = 0.0
                break

        # 대쉬 중과 대쉬 후 무적 시간에는 지면 아래로 내려가지 않는다.
        if (self.dash_timer > 0.0 or self.dash_invuln > 0.0) and self.y < self.ground_y:
            self.y = self.ground_y
            self.vy = 0.0
            self.on_ground = True

        if self.drop_through is not None:
            through = self.drop_through
            if (self.y < through.bottom or self.right <= through.left
                    or self.left >= through.right):
                self.drop_through = None

        self.x = max(self.limit_left, min(self.limit_right, self.x))

        # --- 애니메이션 상태 -------------------------------------------
        if self.dash_timer > 0.0:
            desired = "dash"
        elif self.hit_stun > 0.0:
            desired = "hit"
        elif self.attack_timer > 0.0:
            desired = "attack"
        elif not self.on_ground:
            desired = "jump"
        elif abs(self.vx) > 26.0:
            desired = "run"
        else:
            desired = "idle"

        self.anim_time += dt
        self._set_state(desired, keep_time=(desired == self.state))

    @staticmethod
    def _approach(value, target, delta):
        if value < target:
            return min(value + delta, target)
        return max(value - delta, target)

    def _set_state(self, state, keep_time=False):
        if self.state != state:
            self.state = state
            if not keep_time:
                self.anim_time = 0.0

    # ------------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------------
    def _frame_index(self):
        t = self.anim_time
        if self.state == "idle":
            return IDLE2_CYCLE[int(t / 0.13) % len(IDLE2_CYCLE)]
        if self.state == "run":
            return int(t / 0.035) % 20
        if self.state == "jump":
            if self.vy > 0.0:
                return min(int(t / 0.06), 4)
            return 5 + min(int(t / 0.08), 4)
        if self.state == "attack":
            return min(int(t / 0.055), 9)
        if self.state == "hit":
            return min(int(t / 0.04), 9)
        if self.state == "retire":
            return min(int(t / 0.13), 9)
        return 0

    def _sheet_name(self):
        if self.state in ("run", "jump"):
            return self.state
        if self.state == "idle":
            return "idle2"
        if self.state in ("attack", "hit", "retire"):
            return self.state
        return "idle2"

    def draw(self, camera_x, shake_x=0.0, time=0.0):
        if self.state == "dash":
            draw_dash(self.x - camera_x + shake_x, self.y, self.facing, self.anim_time)
            return
        # 피격 직후에는 깜빡인다.
        if self.invuln > 0.0 and self.state != "retire" and int(self.invuln * 18) % 2 == 0:
            return

        sheet_name = self._sheet_name()
        bob = 0.0
        if self.state == "idle":
            bob = math.sin(time * 3.2) * 1.5

        frame = self._frame_index()
        left, bottom, width, height = _cell_rect(sheet_name, frame)
        sheet = _sheet(sheet_name)
        # 대쉬 후 무적 중에는 반투명하게 그린다.
        alpha = 110 if self.dash_invuln > 0.0 else 255
        pico2d.SDL_SetTextureBlendMode(sheet.texture, pico2d.SDL_BLENDMODE_BLEND)
        pico2d.SDL_SetTextureAlphaMod(sheet.texture, alpha)
        scale = SHEET_SCALE.get(sheet_name, SCALE)
        draw_w = width * scale
        draw_h = height * scale
        flip = "h" if self.facing < 0 else ""
        screen_x = self.x - camera_x + shake_x
        if sheet_name == "idle2":
            screen_x += idle2_shift(frame, scale, self.facing)
        if sheet_name == "retire":
            pad = RETIRE2_PAD[min(frame, len(RETIRE2_PAD) - 1)]
        elif sheet_name == "run":
            pad = RUN_PAD[frame]
        elif sheet_name == "idle2":
            pad = IDLE2_PAD[frame]
        elif sheet_name == "attack":
            pad = ATTACK2_PAD[frame]
        else:
            pad = FOOT_PAD[sheet_name]
        center_y = self.y + draw_h * 0.5 - pad * scale + bob
        sheet.clip_composite_draw(
            left, bottom, width, height, 0.0, flip,
            screen_x, center_y, draw_w, draw_h,
        )
        pico2d.SDL_SetTextureAlphaMod(sheet.texture, 255)

        # 달리는 동안 발밑 먼지를 살짝 표현
        if self.state == "run" and int(time * 12) % 2 == 0:
            pico2d.draw_circle(
                screen_x - self.facing * 18,
                self.y + 4,
                3,
                150, 170, 210, 70,
                filled=True,
            )

    def draw_preview(self, x, y, scale=0.7, frame=0, facing=1):
        """타이틀 화면용 큰 미리보기."""
        # 게임 안과 같은 크기가 되도록, 미리보기 배율을 대기 시트 배율에 맞춘다.
        scale = scale * SHEET_SCALE["idle2"] / SCALE
        index = IDLE2_CYCLE[frame % len(IDLE2_CYCLE)]
        left, bottom, width, height = _cell_rect("idle2", index)
        sheet = _sheet("idle2")
        w = width * scale
        h = height * scale
        center_y = y + h * 0.5 - IDLE2_PAD[index] * scale
        x += idle2_shift(index, scale, facing)
        flip = "h" if facing < 0 else ""
        sheet.clip_composite_draw(
            left, bottom, width, height, 0.0, flip,
            x, center_y, w, h,
        )
