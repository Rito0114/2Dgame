"""3스테이지의 보스: sprites/boss/ 의 전용 스프라이트로 움직인다.

- 등장: Rising → Idle
- 이동/대기: Walk / Idle
- 접촉 공격: Fire, Knife, Throw, Skill1~3 을 번갈아 재생
- 피격: Hit
- 쓰러짐: Retire → Retire2

크기는 주인공과 같고, 체력은 100이다. 공격으로 여러 번 맞춰야 쓰러지고,
쓰러지면 스테이지가 바로 클리어된다.
"""

from boss_sprites import ATTACK_NAMES, BOSS_SPRITES
from girl import Girl

# 시트별 보이는 크기 차이는 BossSprite.scale 이 주인공 크기로 보정한다.
BOSS_SCALE = 1.0
# 충돌 박스는 주인공보다 가로로 1.5배 넓게 잡는다.
BOSS_WIDTH = Girl.HITBOX_W * 1.5
BOSS_HEIGHT = Girl.HITBOX_H
BOSS_HP = 100  # 보스 최대 체력
BASIC_ATTACK_DAMAGE = 2  # 기본 공격(펀치, 밟기) 데미지
SKILL_ATTACK_DAMAGE = 8  # 스킬(대시) 공격 데미지
# 페이즈 구간: 1페이즈 100~67, 2페이즈 66~34, 3페이즈 33~0
PHASE_HP_RANGES = ((100, 67), (66, 34), (33, 0))
PHASE_MIN_HP = (67, 34)  # 각 페이즈를 유지하는 최소 체력
BOSS_SPEED = 105.0  # 플레이어를 향해 걸어가는 속도
ENTRY_WALK_SPEED = 260.0  # 대사 전 연출에서 화면 오른쪽에서 걸어오는 속도
ENTRY_IDLE_TIME = 1.4  # 걸어온 뒤 대사가 시작되기 전까지 멈춰 있는 시간
FLASH_TIME = 0.14  # 맞았을 때 하얗게 번쩍이는 시간

RISING_TIME = BOSS_SPRITES["rising"].duration
IDLE_INTRO_TIME = 1.2  # 등장한 뒤 걷기 전까지 대기하는 시간
HIT_TIME = BOSS_SPRITES["hit"].duration
DEATH_TIME = (BOSS_SPRITES["retire"].duration
              + BOSS_SPRITES["retire2"].duration + 0.4)


def phase_for_hp(hp):
    """체력에 따른 보스 페이즈(1~3)를 돌려준다."""
    if hp >= PHASE_MIN_HP[0]:
        return 1
    if hp >= PHASE_MIN_HP[1]:
        return 2
    return 3


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
        self.walking = False  # 실제로 움직일 때만 걷기 모션, 그 외에는 IDLE
        self.rise_time = 0.0  # 등장 모션 진행 시간
        self.idle_time = IDLE_INTRO_TIME  # 등장 연출 동안에는 제자리에서 대기
        self.hit_time = 0.0  # 피격 모션 진행 시간
        self.anim_time = 0.0  # 걷기/대기 루프용 시간
        self.attack_t = None
        self.attack_duration = 0.0
        self.attack_index = 0  # 다음에 쓸 공격 모션의 번호
        self.attack_hold = 0.0
        self.death_time = 0.0
        self.flash = 0.0
        self.hit_cooldown = 0.0  # 접촉 중 여러 번 맞는 것을 막는다
        self.last_attack = -1  # 같은 공격에 여러 번 맞지 않도록
        self.phase_state = 1  # 체력과 별개로 진행되는 명시적 페이즈(기믹 후 2)
        self.hp_locked = False  # 기믹 중에는 체력이 줄지 않는다
        self.stunned = False  # 딜타임/낙석 기절 상태
        self.stun_sheet = None  # 기절 중 재생할 시트 이름
        self.current_attack = None  # 패턴이 직접 지정한 공격 시트 이름
        self.entry_target = 0.0  # 걸어와서 멈출 x
        self.entry_walking = False  # 화면 밖에서 걸어오는 중
        self.entry_idle = 0.0  # 걸어온 뒤 IDLE 로 멈춰 있는 남은 시간

    @property
    def defeated(self):
        return self.hp <= 0

    @property
    def phase(self):
        """체력 기준 페이즈. 기믹 종료 후에는 2페이즈 이상을 유지한다."""
        return max(phase_for_hp(self.hp), self.phase_state)

    @property
    def entry_done(self):
        """걸어오기와 IDLE 대기가 끝나 대사를 시작해도 되는 상태."""
        return not self.entry_walking and self.entry_idle <= 0.0

    def begin_entry(self, target_x):
        """오른쪽 화면 밖에서 target_x 까지 걸어온 뒤 잠시 IDLE 한다."""
        half = self.width * 0.5
        self.x = self.right - half  # 화면 오른쪽 밖
        self.entry_target = float(target_x)
        self.entry_walking = True
        self.entry_idle = ENTRY_IDLE_TIME
        self.rise_time = RISING_TIME  # 등장 모션은 화면 밖에서 끝난다
        self.idle_time = 0.0
        self.facing = -1
        self.walking = True

    def finish_entry(self):
        """입력으로 등장 연출을 건너뛴다."""
        self.x = self.entry_target
        self.entry_walking = False
        self.entry_idle = 0.0
        self.walking = False

    def rect(self):
        return (self.x - self.width * 0.5, self.y,
                self.width, self.height)

    def _attack_name(self):
        """현재 재생 중인 공격 모션의 시트 이름."""
        index = (self.attack_index - 1) % len(ATTACK_NAMES)
        return ATTACK_NAMES[index]

    def is_attacking(self):
        return self.attack_t is not None and self.attack_t < self.attack_duration

    def play_attack(self, name):
        """패턴이 지정한 공격 모션을 한 번 재생한다."""
        if name not in BOSS_SPRITES or self.is_attacking():
            return False
        self.attack_t = 0.0
        self.attack_duration = BOSS_SPRITES[name].duration
        self.current_attack = name
        self.attack_hold = 0.1
        return True

    def touch(self):
        """플레이어와 닿았을 때 공격 모션을 한 번만 재생한다."""
        if self.current_attack is not None:
            return
        if self.attack_hold <= 0.0 and not self.is_attacking():
            self.attack_t = 0.0
            name = ATTACK_NAMES[self.attack_index % len(ATTACK_NAMES)]
            self.attack_duration = BOSS_SPRITES[name].duration
            self.attack_index += 1
        self.attack_hold = 0.1

    def hurt(self, damage=BASIC_ATTACK_DAMAGE):
        """damage 만큼 체력이 줄고, 0이 되면 쓰러진다."""
        if not self.alive or self.hp_locked or self.hit_cooldown > 0.0:
            return False
        self.hit_cooldown = 0.4
        self.hp = max(0, self.hp - damage)
        self.flash = FLASH_TIME
        self.hit_time = HIT_TIME
        if self.hp == 0:
            self.alive = False
            self.attack_t = None
            self.death_time = 0.0
        return True

    def _update_entry(self, dt):
        """걸어오기 → IDLE 대기. 이 동안에는 플레이어를 쫓지 않는다."""
        if self.entry_walking:
            diff = self.entry_target - self.x
            step = ENTRY_WALK_SPEED * dt
            if abs(diff) <= step:
                self.x = self.entry_target
                self.entry_walking = False
                self.walking = False
            else:
                self.x += step if diff > 0.0 else -step
                self.facing = 1 if diff > 0.0 else -1
                self.walking = True
        else:
            self.walking = False
            self.entry_idle = max(0.0, self.entry_idle - dt)
        half = self.width * 0.5
        self.x = max(self.left + half, min(self.right - half, self.x))

    def update(self, dt, player_x):
        self.anim_time += dt
        self.flash = max(0.0, self.flash - dt)
        self.hit_cooldown = max(0.0, self.hit_cooldown - dt)
        self.attack_hold = max(0.0, self.attack_hold - dt)
        self.hit_time = max(0.0, self.hit_time - dt)
        if not self.alive:
            self.death_time += dt
            return
        if self.entry_walking or self.entry_idle > 0.0:
            self._update_entry(dt)
            return
        if self.rise_time < RISING_TIME:
            self.rise_time = min(RISING_TIME, self.rise_time + dt)
        elif self.idle_time > 0.0:
            self.idle_time = max(0.0, self.idle_time - dt)
        if self.attack_t is not None:
            self.attack_t += dt
            if self.attack_t >= self.attack_duration:
                self.attack_t = None
                self.current_attack = None
                self.attack_index += 1
        if self.stunned:
            self.walking = False
            return
        # 공격/피격/등장 중에는 멈춰 서고, 그 외에는 플레이어 쪽으로 걷는다.
        old_x = self.x
        distance = player_x - self.x
        can_walk = (self.rise_time >= RISING_TIME and self.idle_time <= 0.0
                    and self.hit_time <= 0.0 and not self.is_attacking()
                    and abs(distance) > 40.0)
        if can_walk:
            direction = 1.0 if distance > 0.0 else -1.0
            self.x += direction * BOSS_SPEED * dt
            self.facing = 1 if direction > 0.0 else -1
        half = self.width * 0.5
        self.x = max(self.left + half, min(self.right - half, self.x))
        # 실제로 자리를 옮겼을 때만 걷기 모션을 재생한다.
        self.walking = abs(self.x - old_x) > 0.01

    def draw(self, art, camera_x, shake_x=0.0):
        if not self.alive and self.death_time > DEATH_TIME + 0.3:
            return
        if not self.alive:
            retire = BOSS_SPRITES["retire"]
            if self.death_time < retire.duration:
                name, t = "retire", self.death_time
            else:
                name, t = "retire2", self.death_time - retire.duration
        elif self.stunned:
            name = self.stun_sheet or "retire"
            t = min(self.anim_time, BOSS_SPRITES[name].duration - 0.01)
        elif self.hit_time > 0.0:
            name, t = "hit", HIT_TIME - self.hit_time
        elif self.is_attacking():
            name = self.current_attack or self._attack_name()
            t = self.attack_t
        elif self.rise_time < RISING_TIME:
            name, t = "rising", self.rise_time
        elif self.walking:
            name, t = "walk", self.anim_time
        else:
            name, t = "idle", self.anim_time
        BOSS_SPRITES[name].draw(self.x, self.y, self.facing, t,
                                camera_x, shake_x, BOSS_SCALE)
