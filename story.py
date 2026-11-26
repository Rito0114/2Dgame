"""스테이지 1 오프닝 시나리오 데이터와 재생기.

UI 는 main.py 의 Art/TextRenderer 를 빌려 쓰고, 이 모듈은 대사 순서와
효과(페이드/흔들림/연기/소리cue)의 타이밍만 관리한다.
"""

import math
import random

PORTRAITS = {
    "엘마": "sprites/UI/scenario/SN_ElmaUI.png",
    "곰 수인": "sprites/UI/scenario/SN_BearUI.png",
    "국장": "sprites/UI/scenario/SN_HeadUI.png",
}

REVEAL_SPEED = 26.0  # 글자/초. 타이핑 효과 속도

EFFECT_DURATIONS = {
    "fade_in": 1.30,
    "quake": 1.10,
    "explosion": 1.00,
    "fade_out": 0.95,
    "fade_in_smoke": 1.20,
    "look": 1.00,
    "comm_beep": 0.90,
    "silence": 1.30,
    "comm_end": 0.85,
    "weapon": 1.15,
    "battle": 1.40,
}


def plain_text(text):
    """마크다운 강조(**)는 표시하지 않는다."""
    return text.replace("**", "")


def portrait_path(speaker):
    return PORTRAITS.get(speaker)


def _line(speaker, text):
    return {"kind": "line", "speaker": speaker, "text": text}


def _effect(effect):
    """괄호 연출은 빈 대사 한 턴으로 남기고 효과만 적용한다."""
    return {"kind": "effect", "text": "", "effect": effect}


# 사용자가 준 시나리오를 순서 그대로 옮겼다. 괄호 안 연출은 빈 칸 한 턴으로
# 남기고, 해당 효과만 main.py 가 적용한다.
STAGE1_STORY = (
    _effect("fade_in"),

    _line("엘마", "...아아, 좋네."),
    _line("엘마", "이게 대체 얼마 만의 휴가야..."),
    _line("엘마", "아무런 임무도, 호출도 없이 느긋하게 거리를 걷는 게 얼마 만인지 모르겠네."),
    _line("엘마", "후후... 오늘만큼은 누구의 방해도 받지 않을 거야."),
    _line("엘마", "우선 잭 아저씨네 가게에 들러서 한정판 타르트를 먹고..."),
    _line("엘마", "그다음엔 오랜만에 쇼핑이나 좀 해볼까."),
    _line("엘마", "좋아. 오늘은 정말 완벽한 휴가가 될 것 같아."),

    _effect("quake"),
    _effect("explosion"),
    _effect("fade_out"),
    _effect("fade_in_smoke"),

    _line("엘마", "...으윽."),
    _line("엘마", "대체... 무슨 일이 일어난 거야?"),
    _effect("look"),

    _line("곰 수인", "더러운 인간 놈들...!"),
    _line("곰 수인", "오늘이야말로 모조리 죽여버리겠다!"),
    _line("엘마", "...하아."),
    _line("엘마", "설마 했는데, 역시 루나폴이었나."),
    _line("엘마", "모처럼의 휴가를 아주 제대로 망쳐주는구나..."),

    _effect("comm_beep"),
    _line("국장", "엘마, 들리나? 엘마!"),
    _line("엘마", "...네, 잘 들립니다."),
    _line("엘마", "휴가가 끝났다는 소리까지 아주 선명하게 들리는군요."),
    _line("국장", "상황은 확인했겠지? 루나폴 잔당이 도심 한복판에서 테러를 일으켰네."),
    _line("국장", "민간인 피해가 발생하고 있어. 신속한 대응이 필요하네."),
    _line("엘마", "알고 있습니다. 그런데 지원 병력은요?"),
    _line("국장", "현재 외곽에서 적의 추가 침입을 저지하고 있네."),
    _line("엘마", "...그렇군요."),
    _line("엘마", "그러니까 정리하자면,"),
    _line("엘마", "저는 여기서 혼자 루나폴 놈들을 전부 쓸어버리고,"),
    _line("엘마", "놈들의 보스까지 처리한 다음 돌아오면 된다는 거죠?"),
    _line("국장", "..."),
    _line("국장", "미안하네. 지금 당장 자네에게 의지할 수밖에 없는 상황이야."),
    _line("엘마", "하아... 정말이지."),
    _line("엘마", "슬슬 다른 직장을 알아봐야 하나..."),
    _line("국장", "물론 자네의 희생에 대한 보상은 충분히 준비하겠네."),
    _line("엘마", "...보상이요?"),
    _line("국장", "이번 임무를 성공적으로 완수한다면 특별 포상과 함께,"),
    _line("국장", "**2주간의 특별 휴가**를 보장하지."),

    _effect("silence"),
    _line("엘마", "..."),
    _line("엘마", "브리타니아 정보국 소속 요원, 엘마."),
    _line("엘마", "지금부터 현장 상황을 정리하고 적을 섬멸하겠습니다."),
    _line("국장", "...방금 전까지 퇴직을 고민하던 사람 맞나?"),
    _line("엘마", "통신 상태가 좋지 않은 것 같습니다. 잘 안 들리네요."),
    _line("국장", "...속이 훤히 보이는군."),

    _effect("comm_end"),
    _effect("weapon"),
    _line("엘마", "좋아. 그럼 어디..."),
    _line("엘마", "내 휴가를 망친 대가가 얼마나 비싼지 알려줘야겠네."),
    _effect("battle"),
)


class StoryPlayer:
    """대사를 한 글자씩 보여주고, 입력으로만 다음 턴으로 넘어간다."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.steps = STAGE1_STORY
        self.reset()

    def reset(self):
        self.index = 0
        self.elapsed = 0.0
        self.finished = False
        self.smoke_scene = False
        self.flash = 0.0
        self.revealed = 0.0  # 현재 대사에서 표시된 글자 수
        self.last_speaker = "엘마"  # 빈 연출 턴에도 마지막 초상화를 유지
        rng = random.Random(11)
        self.smoke_puffs = [
            [rng.uniform(0, self.width), rng.uniform(0, self.height),
             rng.uniform(46, 130), rng.uniform(0.25, 0.75), rng.random() * 6.28]
            for _ in range(22)
        ]
        return self._on_enter(self.current())

    # -- 현재 상태 ------------------------------------------------------
    def current(self):
        if self.finished or self.index >= len(self.steps):
            return None
        return self.steps[self.index]

    @property
    def speaker(self):
        step = self.current()
        if step and step["kind"] == "line":
            return step.get("speaker")
        return self.last_speaker

    @property
    def text(self):
        step = self.current()
        return plain_text(step["text"]) if step else ""

    @property
    def visible_text(self):
        """지금까지 타이핑으로 드러난 부분만 돌려준다."""
        return self.text[:int(self.revealed)]

    @property
    def is_revealing(self):
        return int(self.revealed) < len(self.text)

    def reveal_all(self):
        """스페이스 입력으로 현재 대사를 한 번에 모두 표시한다."""
        self.revealed = float(len(self.text))

    def duration(self, step=None):
        step = step if step is not None else self.current()
        if step is None:
            return 0.0
        if step["kind"] == "line":
            length = len(plain_text(step["text"]))
            return min(4.0, max(1.35, 1.0 + length * 0.06))
        return EFFECT_DURATIONS.get(step.get("effect"), 1.2)

    @property
    def progress(self):
        duration = self.duration()
        return min(1.0, self.elapsed / duration) if duration > 0 else 1.0

    def fade_alpha(self):
        step = self.current()
        if step is None:
            return 0
        effect = step.get("effect")
        t = self.progress
        if effect == "fade_in" or effect == "fade_in_smoke":
            return int(255 * (1.0 - t))
        if effect == "fade_out":
            return int(255 * t)
        return 0

    def portrait_sway(self):
        """'[주변을 둘러보는 엘마]' 연출에서 초상화가 살짝 흔들린다."""
        step = self.current()
        if not step or step.get("effect") != "look":
            return 0.0
        return math.sin(self.progress * 12.0) * 14.0

    # -- 진행 ----------------------------------------------------------
    def _on_enter(self, step):
        if step is None:
            return None
        self.revealed = 0.0
        if step["kind"] == "line":
            self.last_speaker = step["speaker"]
        effect = step.get("effect")
        if effect == "fade_in_smoke":
            self.smoke_scene = True
        if effect == "explosion":
            self.flash = 1.0
        elif effect == "quake":
            self.flash = 0.35
        return step

    def advance(self):
        """다음 단계로 넘어간다. 마지막 단계면 finished 를 켠다."""
        if self.finished:
            return None
        if self.index + 1 >= len(self.steps):
            self.finished = True
            return None
        self.index += 1
        self.elapsed = 0.0
        return self._on_enter(self.current())

    def update(self, dt):
        """글자/연출 타이밍만 흘려보낸다. 턴은 입력으로만 넘어간다."""
        if self.finished:
            return
        step = self.current()
        if step is None:
            self.finished = True
            return

        self.elapsed += dt
        if step["kind"] == "line" and self.is_revealing:
            self.revealed = min(float(len(self.text)),
                                self.revealed + dt * REVEAL_SPEED)
        if self.flash > 0.0:
            self.flash = max(0.0, self.flash - dt * 2.2)
        if self.smoke_scene:
            for puff in self.smoke_puffs:
                puff[0] += math.sin(self.elapsed * 0.7 + puff[4]) * 12.0 * dt
                puff[1] += puff[3] * 42.0 * dt
                if puff[1] > self.height + 80:
                    puff[1] = -80
                    puff[0] = random.uniform(0, self.width)
