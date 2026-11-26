"""3스테이지의 보스: 기존 곰 스프라이트를 키워서 만든 큰 곰.

별도의 보스 그림이 없으므로 bear.py 의 곰 그림을 확대해 그린다.
공격으로 여러 번 맞춰야 쓰러지고, 쓰러지면 스테이지가 바로 클리어된다.
"""

from bear import (ATTACK_DURATION, BEAR_HEIGHT, BEAR_WIDTH, DEATH_TIME,
                  SCALE, draw_bear)

BOSS_SCALE = SCALE * 1.9  # 일반 곰보다 약 1.9배 크게
BOSS_WIDTH = int(BEAR_WIDTH * BOSS_SCALE / SCALE)
BOSS_HEIGHT = int(BEAR_HEIGHT * BOSS_SCALE / SCALE)
BOSS_HP = 8  # 쓰러뜨리는 데 필요한 공격 횟수
BOSS_SPEED = 105.0  # 플레이어를 향해 걸어가는 속도
FLASH_TIME = 0.14  # 맞았을 때 하얗게 번쩍이는 시간


class Boss:
    def __init__(self, x, y, left, right):
        self.x = float(x)
        self.y = float(y)
        self.left = float(left)
        self.right = float(right)
        self.width = BOSS_WIDTH
        self.height = BOSS_HEIGHT
        self.max_hp = BOSS_HP
        self.hp = BOSS_HP
        self.alive = True
        self.vx = -BOSS_SPEED
        self.facing = -1
        self.anim_time = 0.0
        self.attack_t = None
        self.attack_hold = 0.0
        self.death_time = 0.0
        self.flash = 0.0
        self.hit_cooldown = 0.0  # 접촉 중 여러 번 맞는 것을 막는다
        self.last_attack = -1  # 같은 공격에 여러 번 맞지 않도록

    @property
    def defeated(self):
        return self.hp <= 0

    def rect(self):
        return (self.x - self.width * 0.5, self.y,
                self.width, self.height)

    def is_attacking(self):
        return self.attack_t is not None and self.attack_t < ATTACK_DURATION

    def touch(self):
        """플레이어와 닿았을 때 공격 모션을 한 번만 재생한다."""
        if self.attack_hold <= 0.0 and not self.is_attacking():
            self.attack_t = 0.0
        self.attack_hold = 0.1

    def hurt(self):
        """한 번 맞으면 체력이 1 줄고, 0이 되면 쓰러진다."""
        if not self.alive or self.hit_cooldown > 0.0:
            return False
        self.hit_cooldown = 0.4
        self.hp = max(0, self.hp - 1)
        self.flash = FLASH_TIME
        if self.hp == 0:
            self.alive = False
            self.attack_t = None
            self.death_time = 0.0
        return True

    def update(self, dt, player_x):
        self.anim_time += dt
        self.flash = max(0.0, self.flash - dt)
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)
        self.attack_hold = max(0.0, self.attack_hold - dt)
        if not self.alive:
            self.death_time += dt
            return
        if self.attack_t is not None:
            self.attack_t += dt
            if self.attack_t >= ATTACK_DURATION:
                self.attack_t = None
        # 공격 중에는 멈춰 서고, 그 외에는 플레이어 쪽으로 천천히 걷는다.
        distance = player_x - self.x
        if not self.is_attacking() and abs(distance) > 40.0:
            direction = 1.0 if distance > 0.0 else -1.0
            self.x += direction * BOSS_SPEED * dt
            self.facing = 1 if direction > 0.0 else -1
        half = self.width * 0.5
        self.x = max(self.left + half, min(self.right - half, self.x))

    def draw(self, art, camera_x, shake_x=0.0):
        if not self.alive and self.death_time > DEATH_TIME + 0.3:
            return
        if not self.alive:
            state, t = "retire", self.death_time
        elif self.is_attacking():
            state, t = "attack", self.attack_t
        else:
            state, t = "walk", self.anim_time
        draw_bear(self.x, self.y, self.facing, state, t, camera_x, shake_x,
                  scale=BOSS_SCALE)
        if self.alive and self.flash > 0.0:
            x = self.x - camera_x + shake_x
            art.blit(art.disc((255, 255, 255)), x,
                     self.y + self.height * 0.45,
                     self.width * 1.1, self.height * 0.95, alpha=110)
