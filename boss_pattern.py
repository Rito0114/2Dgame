"""보스 1페이즈 패턴 상태 머신.

기존 구조를 최대한 재사용한다.
- 보스 애니메이션: BOSS_SPRITES / Boss.play_attack()
- 총알: cat.Bullet (vx/vy 확장)
- 경고/낙하/폭발: bomb.Bomb + BombField
- 피격: Girl.take_hit() (무적 시간 유지)
- 이펙트: Game.burst / shake / sfx

상태:
idle / melee / ranged / downtime / gimmick_start / grenade
/ aimed_grenade / rock_stun / rock_stun_down / phase2
"""

import math
import os

import pico2d

from bomb import Bomb, ELLIPSE_W
from cat import Bullet

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STONE_FILE = os.path.join(BASE_DIR, "sprites", "object", "stone.png")
_stone_image = None

# ---------------------------------------------------------------------------
# 1페이즈 기본 공격
# ---------------------------------------------------------------------------
MELEE_COOLDOWN = 1.2
MELEE_STRIKE_TIME = 0.16
MELEE_ANIM_TIME = 0.8
RANGED_COOLDOWN = 5.0
RANGED_SHOTS = (2, 1, 3)
RANGED_GAP = (1.0, 0.5)
FIRE_ANIM_TIME = 0.8
RANGED_TOTAL = 3 * FIRE_ANIM_TIME + sum(RANGED_GAP)
BULLET_SPEED = 460.0
MUZZLE_DX = 88.0
MUZZLE_DY_RATIO = 0.62
DOWNTIME_INTERVAL = 20.0
DOWNTIME_DURATION = 10.0

# ---------------------------------------------------------------------------
# 1페이즈 기믹
# ---------------------------------------------------------------------------
GIMMICK_HP = 67
GIMMICK_START_TIME = 0.8
VOLLEY_COUNT = 3
VOLLEY_BOMBS = 5
THROW_ANIM_TIME = 0.8
VOLLEY_GAP = 1.6
AIM_TRACK_TIME = 2.0
AIM_LOCK_BEFORE = 1.0
ROCK_FALL_TIME = 0.6
ROCK_STUN_TIME = 5.0
PHASE2_ANIM_TIME = 0.9
DEADSHOT_SPEED = 1400.0

BOMB_MARGIN = ELLIPSE_W * 0.5
AIM_STATES = ("gimmick_start", "grenade", "aimed_grenade",
              "rock_stun", "rock_stun_down", "phase2")


class BossPattern:
    def __init__(self, boss, game, ground_y, sky_y):
        self.boss = boss
        self.game = game
        self.ground_y = ground_y
        self.sky_y = sky_y
        self.state = "idle"
        self.time = 0.0
        self.melee_cooldown = 2.0
        self.ranged_cooldown = RANGED_COOLDOWN
        self.downtime_timer = DOWNTIME_INTERVAL

        self._ranged_fired = 0
        self._melee_hit_done = False
        self.volley = 0
        self.aim_pos = None
        self.aim_x = 0.0
        self.last_bomb = None
        self.last_hit_handled = False
        self.handled_bombs = set()
        self.rock = None
        self.deadshot = None
        self.gimmick_done = False  # 기믹 완료 후 HP 67이어도 재시작하지 않는다

    # ------------------------------------------------------------------
    # 공통 유틸
    # ------------------------------------------------------------------
    def _enter(self, state):
        self.state = state
        self.time = 0.0

    def _clear_attack(self):
        self.boss.attack_t = None
        self.boss.current_attack = None

    def _touching_girl(self):
        gx, gy, gw, gh = self.game.girl.rect()
        bx, by, bw, bh = self.boss.rect()
        return (gx < bx + bw and gx + gw > bx
                and gy < by + bh and gy + gh > by)

    def _face_girl(self):
        self.boss.facing = 1 if self.game.girl.x >= self.boss.x else -1

    def _muzzle(self):
        return (self.boss.x + self.boss.facing * MUZZLE_DX,
                self.boss.y + self.boss.height * MUZZLE_DY_RATIO)

    def _shoot(self, count):
        girl = self.game.girl
        sx, sy = self._muzzle()
        for i in range(count):
            tx = girl.focus_x() + (i - (count - 1) * 0.5) * 18.0
            ty = girl.y + girl.HITBOX_H * 0.55
            self.game.bullets.append(self._aimed_bullet(sx, sy, tx, ty))
        self.game.sfx.play("gunfire_sound.mp3", 0.5)

    def _aimed_bullet(self, sx, sy, tx, ty, speed=BULLET_SPEED):
        dx, dy = tx - sx, ty - sy
        length = max(1.0, math.hypot(dx, dy))
        return Bullet(sx, sy, 1 if dx >= 0.0 else -1,
                      vx=dx / length * speed, vy=dy / length * speed)

    def _clamp_x(self, x):
        # 경고 타원이 화면 안에 들어오도록 한다.
        camera = self.game.camera
        return max(camera + BOMB_MARGIN,
                   min(camera + 1280 - BOMB_MARGIN, x))

    def _throw(self, count):
        girl = self.game.girl
        for i in range(count):
            x = girl.focus_x() + (i - (count - 1) * 0.5) * 120.0
            bomb = Bomb(self._clamp_x(x), self.ground_y, self.sky_y)
            bomb.boss_pattern = True  # 기본 폭탄 피격 처리를 건너뛴다.
            self.game.bombs.bombs.append(bomb)
        self.game.sfx.play("bomb_sound.mp3", 0.35)

    def _throw_at(self, x):
        bomb = Bomb(x, self.ground_y, self.sky_y)
        bomb.boss_pattern = True
        self.game.bombs.bombs.append(bomb)
        self.last_bomb = bomb
        self.last_hit_handled = False
        self.game.sfx.play("bomb_sound.mp3", 0.35)

    def _grenade_hit(self, bomb):
        """바닥 타원 범위만 검사한다. 공중 여부와 무관하게 피격."""
        if self.game.girl.take_hit(bomb.x):
            self.game.sfx.play("female_deathsound.mp3")
            self.game.shake = max(self.game.shake, 11.0)

    def _deadshot(self):
        # 기둥이 없으면 피할 수 없는 총알 1발. 맞으면 즉사.
        girl = self.game.girl
        sx, sy = self._muzzle()
        bullet = self._aimed_bullet(
            sx, sy, girl.focus_x(), girl.y + girl.HITBOX_H * 0.5,
            DEADSHOT_SPEED)
        bullet.kill_player = True
        self.deadshot = bullet
        self.game.bullets.append(bullet)
        self.game.sfx.play("gunfire_sound.mp3", 0.7)

    def _update_deadshot(self, dt):
        if self.deadshot is None:
            return
        if not self.deadshot.alive:
            self.deadshot = None
            if self.game.girl.state != "retire" and self.state == "aimed_grenade":
                # 혹시 빗나가면 잠금을 풀고 기본 전투로 되돌린다.
                self.gimmick_done = True
                self.boss.hp_locked = False
                self.aim_pos = None
                self._enter("idle")
            return
        girl = self.game.girl
        dx = girl.focus_x() - self.deadshot.x
        dy = girl.y + girl.HITBOX_H * 0.5 - self.deadshot.y
        length = max(1.0, math.hypot(dx, dy))
        self.deadshot.vx = dx / length * DEADSHOT_SPEED
        self.deadshot.vy = dy / length * DEADSHOT_SPEED

    def _begin_downtime(self):
        self.boss.stunned = True
        self.boss.stun_sheet = "retire"
        self._clear_attack()
        self._enter("downtime")

    def _end_downtime(self):
        self.boss.stunned = False
        self.boss.stun_sheet = None
        self.boss.anim_time = 0.0
        self.downtime_timer = DOWNTIME_INTERVAL
        self._enter("idle")

    def _begin_gimmick(self):
        self.boss.hp_locked = True
        self.boss.stunned = False
        self.boss.stun_sheet = None
        self._clear_attack()
        self.downtime_timer = DOWNTIME_INTERVAL
        self.volley = 0
        self.aim_pos = None
        self.last_bomb = None
        self.last_hit_handled = False
        self.rock = None
        self.deadshot = None
        self.handled_bombs = set()
        self._enter("gimmick_start")

    def _next_volley(self):
        self.volley += 1
        self._face_girl()
        self.boss.play_attack("throw")
        self._throw(VOLLEY_BOMBS)
        self._enter("grenade")

    def on_bombs_landed(self, bombs):
        """일반 수류탄 착탄: 바닥 타원 안이면 공중 여부와 무관하게 피격."""
        for bomb in bombs:
            if not getattr(bomb, "boss_pattern", False):
                continue
            if bomb is self.last_bomb or bomb in self.handled_bombs:
                continue
            self.handled_bombs.add(bomb)
            if abs(self.game.girl.focus_x() - bomb.x) <= ELLIPSE_W * 0.5:
                self._grenade_hit(bomb)

    # ------------------------------------------------------------------
    # 상태 업데이트
    # ------------------------------------------------------------------
    def update(self, dt):
        boss = self.boss
        if not boss.alive:
            return
        self.time += dt
        self._update_deadshot(dt)

        # HP 67 이하 감지는 한 번만 진입한다.
        if not self.gimmick_done and self.state not in AIM_STATES \
                and boss.hp <= GIMMICK_HP:
            self._begin_gimmick()

        getattr(self, "_state_" + self.state)(dt)

    def _state_idle(self, dt):
        boss = self.boss
        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)
        self.ranged_cooldown = max(0.0, self.ranged_cooldown - dt)
        self.downtime_timer = max(0.0, self.downtime_timer - dt)

        if self.downtime_timer <= 0.0:
            self._begin_downtime()
            return
        if self._touching_girl():
            if self.melee_cooldown <= 0.0:
                self._face_girl()
                self.boss.play_attack("knife")
                self._melee_hit_done = False
                self._enter("melee")
            return
        if self.ranged_cooldown <= 0.0:
            self.ranged_cooldown = RANGED_COOLDOWN
            self._ranged_fired = 0
            self._face_girl()
            self.boss.play_attack("fire")
            self._shoot(RANGED_SHOTS[0])
            self._enter("ranged")

    def _state_melee(self, dt):
        if not self._melee_hit_done and self.time >= MELEE_STRIKE_TIME \
                and self._touching_girl():
            if self.game.girl.take_hit(self.boss.x):
                self._melee_hit_done = True
                self.game.sfx.play("female_deathsound.mp3")
                self.game.shake = max(self.game.shake, 11.0)
                self.game.burst(self.game.girl.x, self.game.girl.y + 100,
                                (255, 120, 140), 16, 320, 0.6, 4)
                if self.game.girl.hp <= 0:
                    self.game.best_score = max(self.game.best_score,
                                               self.game.score)
        if self.time >= MELEE_ANIM_TIME:
            self.melee_cooldown = MELEE_COOLDOWN
            self._clear_attack()
            self._enter("idle")

    def _state_ranged(self, dt):
        if self._ranged_fired == 0 and \
                self.time >= FIRE_ANIM_TIME + RANGED_GAP[0]:
            self._clear_attack()
            self._face_girl()
            self.boss.play_attack("fire")
            self._shoot(RANGED_SHOTS[1])
            self._ranged_fired = 1
        elif self._ranged_fired == 1 and \
                self.time >= 2 * FIRE_ANIM_TIME + sum(RANGED_GAP):
            self._clear_attack()
            self._face_girl()
            self.boss.play_attack("fire")
            self._shoot(RANGED_SHOTS[2])
            self._ranged_fired = 2
        if self.time >= RANGED_TOTAL:
            self._clear_attack()
            self._ranged_fired = 0
            self._enter("idle")

    def _state_downtime(self, dt):
        if self.time >= DOWNTIME_DURATION:
            self._end_downtime()

    def _state_gimmick_start(self, dt):
        if self.time >= GIMMICK_START_TIME:
            self._next_volley()

    def _state_grenade(self, dt):
        if self.time < THROW_ANIM_TIME + VOLLEY_GAP:
            return
        self._clear_attack()
        if self.volley < VOLLEY_COUNT:
            self._next_volley()
            return
        # 마지막 조준 수류탄.
        self._face_girl()
        self.boss.play_attack("throw")
        x = self._clamp_x(self.game.girl.focus_x())
        self._throw_at(x)
        self.aim_pos = (x, self.ground_y)
        self._enter("aimed_grenade")

    def _state_aimed_grenade(self, dt):
        if self.time < AIM_TRACK_TIME - AIM_LOCK_BEFORE:
            self.aim_x = self._clamp_x(self.game.girl.focus_x())
            self.aim_pos = (self.aim_x, self.ground_y)
            if self.last_bomb is not None:
                # 투척 중에도 조준 위치를 실시간으로 갱신한다.
                self.last_bomb.x = self.aim_x
            return
        if self.last_hit_handled or self.last_bomb is None:
            return
        if not self.last_bomb.exploded:
            return
        self.last_hit_handled = True
        self._grenade_hit(self.last_bomb)

        scenery = self.game.world.scenery
        if scenery is None or scenery.pillar_at(self.aim_x) is None:
            self._deadshot()
        else:
            self.rock = {
                "x": self.boss.x,
                "target": self.boss.y + self.boss.height * 0.8,
                "t": 0.0,
            }
            self.game.shake = max(self.game.shake, 24.0)
            self.game.sfx.play("bomb_sound.mp3", 0.5)
            self.game.burst(self.boss.x, self.rock["target"],
                            (150, 150, 165), 24, 340, 0.7, 5)
            self._clear_attack()
            self._enter("rock_stun")

    def _state_rock_stun(self, dt):
        if self.rock is None:
            return
        self.rock["t"] += dt
        if self.rock["t"] >= ROCK_FALL_TIME:
            self.rock = None
            self.boss.stunned = True
            self.boss.stun_sheet = "retire2"
            self.boss.anim_time = 0.0
            self.game.shake = max(self.game.shake, 12.0)
            self._enter("rock_stun_down")

    def _state_rock_stun_down(self, dt):
        if self.time >= ROCK_STUN_TIME:
            self.boss.stunned = False
            self.boss.stun_sheet = None
            self.boss.anim_time = 0.0
            self.boss.phase_state = 2
            self.boss.hp_locked = False
            self.gimmick_done = True
            self.downtime_timer = DOWNTIME_INTERVAL
            self.ranged_cooldown = RANGED_COOLDOWN
            self.melee_cooldown = MELEE_COOLDOWN
            self.aim_pos = None
            self._enter("phase2")

    def _state_phase2(self, dt):
        self.boss.phase_state = 2
        if self.time >= PHASE2_ANIM_TIME:
            self._enter("idle")

    # ------------------------------------------------------------------
    # 그리기
    # ------------------------------------------------------------------
    def draw(self, art, camera_x, shake_x):
        global _stone_image
        if self.rock is not None:
            if _stone_image is None:
                _stone_image = pico2d.load_image(STONE_FILE)
            scale = 0.22
            t = min(1.0, self.rock["t"] / ROCK_FALL_TIME)
            y = self.sky_y + (self.rock["target"] - self.sky_y) * t * t
            left = self.rock["x"] - camera_x + shake_x - 1028 * scale
            art.blit_to(_stone_image, left, y - 250 * scale,
                        _stone_image.w * scale, _stone_image.h * scale)
        if self.aim_pos is not None and self.state == "aimed_grenade":
            disc = art.disc((235, 40, 40))
            x = self.aim_pos[0] - camera_x + shake_x
            art.blit(disc, x, self.aim_pos[1], ELLIPSE_W, 92, 200)
