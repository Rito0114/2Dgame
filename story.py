"""스테이지별 오프닝 시나리오 데이터와 재생기.

UI 는 main.py 의 Art/TextRenderer 를 빌려 쓰고, 이 모듈은 대사 순서와
효과(페이드/흔들림/연기/소리cue)의 타이밍만 관리한다.
"""

import math
import random

PORTRAITS = {
    "엘마": "sprites/UI/scenario/SN_ElmaUI.png",
    "곰 수인": "sprites/UI/scenario/SN_BearUI.png",
    "국장": "sprites/UI/scenario/SN_HeadUI.png",
    "블랙 하운드": "sprites/UI/scenario/SN_BlackUI.png",
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


# 스테이지 2: 중심지 진입 직후, 스킬 정보 팝업 전에 재생된다.
STAGE2_STORY = (
    _effect("fade_in"),

    _line("엘마", "브리타니아 정보국, 요원 엘마입니다."),
    _line("엘마", "외곽 구역의 적을 모두 정리하고 중심지에 진입했습니다."),
    _line("국장", "수고했네, 엘마. 생각보다 빠르게 처리했군."),
    _line("국장", "그런데... 한 가지 좋지 않은 소식이 있네."),
    _line("엘마", "..."),
    _line("엘마", "제발 그 말은 하지 마세요."),
    _line("엘마", "국장님 입에서 그 말이 나올 때마다 꼭 일이 커지더라고요."),
    _line("국장", "하하... 자네도 참 눈치가 빠르군."),
    _line("엘마", "웃으면서 넘길 일이 아니잖아요!"),
    _line("국장", "아무튼, 새로 입수한 정보에 따르면 루나폴 놈들이 화기를 소지하고 있다고 하네."),
    _line("엘마", "...화기요?"),
    _line("국장", "그래. 권총을 보유하고 있다는군."),
    _line("엘마", "잠깐만요. 지금까지 상대했던 놈들은 고작 몽둥이나 휘두르던 녀석들이었잖아요?"),
    _line("국장", "그것뿐만이 아닐세."),
    _line("엘마", "...설마요."),
    _line("국장", "박격포까지 보유하고 있다는 정보가 들어왔네."),
    _line("엘마", "**박격포요?!**"),
    _line("국장", "그래. 아무래도 이번에는 제대로 무장한 모양이야."),
    _line("엘마", "아니, 잠깐만요!"),
    _line("엘마", "박격포라면 포탄을 쏘는 그 박격포 말씀이시죠?!"),
    _line("국장", "다른 박격포도 있나?"),
    _line("엘마", "그걸 지금 농담이라고 하시는 거예요?!"),
    _line("국장", "아무튼 조심하게. 직격당하면 부상 정도로 끝나지는 않을 테니 말이야."),
    _line("엘마", "..."),
    _line("엘마", "국장님."),
    _line("엘마", "저, 지금이라도 사직서 제출하면 안 될까요?"),
    _line("국장", "안 되겠지?"),
    _line("엘마", "...진짜 빌어먹을 직장이네."),
    _line("국장", "하하. 그래도 너무 걱정하지 말게."),
    _line("국장", "자네에게 도움이 될 만한 물건을 하나 보내두었네."),
    _line("엘마", "물건이요?"),
    _line("국장", "임플란트일세. 전투에 활용할 수 있도록 특별히 준비했네."),
    _line("국장", "자세한 사용법은 전달된 자료를 참고하도록 하게."),
    _line("엘마", "아니, 잠깐만요. 임플란트라니, 그게 무슨..."),
    _line("국장", "그럼 행운을 빌겠네. 임무가 끝나면 연락하게."),
    _line("엘마", "국장님? 잠깐만요!"),

    _effect("comm_end"),

    _line("엘마", "..."),
    _line("엘마", "국장님?"),
    _line("엘마", "야?!"),
    _line("엘마", "이 망할 국장 놈아!!"),

    _effect("silence"),

    _line("엘마", "하아..."),
    _line("엘마", "좋아. 일단 이 임플란트라는 것부터 확인해 보자."),
)

# 스테이지 2 클리어 직후. 끝나면 WARNING → 보스 스테이지로 이어진다.
STAGE2_END_STORY = (
    _effect("fade_in"),

    _line("엘마", "...중심지의 적들을 모두 제압했습니다."),
    _line("국장", "수고했네, 엘마. 임플란트는 쓸 만하던가?"),
    _line("엘마", "성능은 꽤 괜찮더군요. 덕분에 큰 도움이 됐습니다."),
    _line("엘마", "그런데 한 가지 궁금한 게 있는데요."),
    _line("국장", "뭔가?"),
    _line("엘마", "'싼데 안 비슷한'이라는 이름은 대체 누가 지은 거죠?"),

    _effect("silence"),

    _line("국장", "...엔지니어 놈들의 유머 감각이야 뭐, 늘 그렇지."),
    _line("엘마", "그걸 유머라고 받아들여야 하는 건가요..."),
    _line("국장", "아무튼, 잡담은 여기까지 하도록 하지."),
    _line("국장", "자네가 있는 곳에서 멀지 않은 지역에 루나폴의 보스가 있다는 정보가 들어왔네."),
    _line("엘마", "블랙 말인가요?"),
    _line("엘마", "뭐, 그 녀석이라면 별로 걱정할 것도 없겠네요. 저번에도 별 볼 일 없었잖아요."),
    _line("국장", "이번에는 이야기가 다르네."),
    _line("엘마", "...네?"),
    _line("국장", "지난번 탈옥 사건 이후로 상당히 강해졌다는 정보가 들어왔어."),
    _line("엘마", "...얼마나 강해졌는데요?"),
    _line("국장", "글쎄... 강해졌다고 해 봤자 평소 전투력의 11배에서 12배 정도라더군."),

    _effect("silence"),

    _line("엘마", "..."),
    _line("엘마", "지금 장난하세요?"),
    _line("국장", "내가 지금 장난이나 칠 상황으로 보이나?"),
    _line("엘마", "하아..."),
    _line("엘마", "알겠습니다. 일단 확인해 보도록 하죠."),
    _line("엘마", "뭐, 이쯤 되면 죽어서 쉬는 것도 나쁘지 않겠네요."),
    _line("국장", "아니, 죽지 말고 무사히 돌아와 줬으면 하네만..."),
    _line("엘마", "그렇게 걱정되시면 지원 병력이라도 보내주시죠."),

    _effect("silence"),

    _line("엘마", "..."),
    _line("엘마", "국장님?"),

    _effect("comm_end"),

    _line("엘마", "..."),
    _line("엘마", "설마 또 멋대로 끊은 거야?"),
    _line("엘마", "진짜... 돌아가기만 해 봐."),
    _line("엘마", "그때는 정말 가만 안 둘 테니까..."),

    _effect("weapon"),

    _line("엘마", "...좋아."),
    _line("엘마", "어디 얼마나 강해졌는지 직접 확인해 보자."),
)

# 스테이지 3: WARNING 후 보스가 걸어나와 IDLE 로 멈춘 뒤 재생된다.
STAGE3_STORY = (
    _line("블랙 하운드", "...어라?"),
    _line("블랙 하운드", "이게 누구야. 내 단골손님, 엘마 골드윈 아니신가?"),
    _line("엘마", "누가 들으면 오해하겠네."),
    _line("엘마", "난 당신 같은 사람을 단골로 둔 적 없거든?"),
    _line("블랙 하운드", "하! 그렇게 여러 번이나 날 잡아가 놓고 그런 소리를 하다니."),
    _line("블랙 하운드", "이 정도면 단골손님 대우라도 해줘야 하는 거 아닌가?"),
    _line("엘마", "뭐, 그건 틀린 말은 아니네."),
    _line("엘마", "그런데 안타깝게도 이번에도 잡아가야 하거든."),
    _line("엘마", "그러니까 그냥 얌전히 두 손 들고 항복하는 건 어때?"),
    _line("블랙 하운드", "미안하지만, 이번에는 그럴 생각이 없어서 말이야."),
    _line("블랙 하운드", "나도 지난번처럼 당하고만 있을 생각은 없거든."),
    _line("블랙 하운드", "내가 얼마나 강해졌는지 직접 보여주지."),
    _line("블랙 하운드", "오히려 네 목숨이 걱정되는군."),
    _line("블랙 하운드", "죽고 싶지 않다면 지금이라도 도망치는 게 좋을 거야."),
    _line("엘마", "푸흐..."),
    _line("엘마", "그래? 그렇게 자신만만하다니 기대되는데?"),
    _line("엘마", "뭐, 아무리 강해져 봤자..."),
    _line("엘마", "개미에서 파리 정도로 승격한 수준이겠지만."),
    _line("블랙 하운드", "..."),
    _line("블랙 하운드", "이 자식이..."),
    _line("엘마", "어머, 왜 그래?"),
    _line("엘마", "설마 긁혔어?"),
    _line("블랙 하운드", "닥쳐라."),
    _line("블랙 하운드", "오늘 여기서 네놈을 반드시 죽여주마."),
    _line("엘마", "그래, 어디 한번 해보자."),
)

STORY_BY_STAGE = {
    1: STAGE1_STORY,
    2: STAGE2_STORY,
    3: STAGE3_STORY,
    "2_end": STAGE2_END_STORY,
}

# 대사 종료 후 화면 중앙에 띄우는 두 줄(큰 제목, 작은 부제).
TITLE_BY_STAGE = {
    1: ("STAGE 1", "루나폴 갱을 소탕하고 중심지로 진입하라"),
    2: ("STAGE 2", "무장한 루나폴을 저지하고 임무를 완수하라"),
}


def story_steps(key):
    """스테이지 번호 또는 '2_end' 같은 키로 시나리오 단계를 돌려준다."""
    return STORY_BY_STAGE.get(key, ())


def stage_title(stage):
    """(큰 제목, 작은 부제). 정의되지 않은 스테이지는 제목을 숨긴다."""
    return TITLE_BY_STAGE.get(stage, ("", ""))


class StoryPlayer:
    """대사를 한 글자씩 보여주고, 입력으로만 다음 턴으로 넘어간다."""

    def __init__(self, width, height, stage=1):
        self.width = width
        self.height = height
        self.key = stage
        self.stage = stage if isinstance(stage, int) else 2
        self.steps = story_steps(stage)
        self.reset()

    def reset(self, key=None):
        if key is not None:
            self.key = key
            self.steps = story_steps(key)
            if isinstance(key, int):
                self.stage = key
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
        """대사는 타이핑만, 빈 연출 턴은 시간이 지나면 자동으로 넘어간다."""
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

        # 괄호 연출(빈 턴)은 스페이스 없이 이어진다. 대사는 입력 대기.
        if step["kind"] == "effect" and self.elapsed >= self.duration(step):
            return self.advance()
        return None
