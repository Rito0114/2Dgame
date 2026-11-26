"""배경음악과 효과음 재생 (SDL_mixer).

- Bgm: 배경음악. 한 번에 한 곡만 반복 재생하고, 스테이지가 바뀌면 곡을 바꾼다.
- Sfx: 효과음. 짧은 소리를 겹쳐서 재생한다.

일시정지 메뉴의 옵션에서 배경음악/효과음 음량과 전체 음소거를 조절할 수 있다.
오디오 장치를 열 수 없으면 아무것도 재생하지 않는다.
"""

import os

import sdl2.sdlmixer as mix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, "sound")
MAX_VOLUME = mix.MIX_MAX_VOLUME

# 곡/효과음 자체의 섞임 비율은 유지한 채, 옵션의 마스터 음량으로 전체를 조절한다.
MUSIC_LEVEL = int(MAX_VOLUME * 0.35)
DEFAULT_SFX_LEVEL = int(MAX_VOLUME * 0.7)
BGM_VOLUME = MAX_VOLUME  # 옵션: 배경음악 음량 (0 ~ MAX_VOLUME)
SFX_VOLUME = MAX_VOLUME  # 옵션: 효과음 음량 (0 ~ MAX_VOLUME)
MUTED = False  # 옵션: 전체 음소거

# 파일별 효과음 음량(기본값은 DEFAULT_SFX_LEVEL). 최대치를 넘을 수 없다.
SFX_VOLUMES = {
    "falling_sound.mp3": MAX_VOLUME,
    "checkpoint_sound.mp3": MAX_VOLUME,
    "jump_sound.mp3": MAX_VOLUME,
    "heal_sound.mp3": int(MAX_VOLUME * 0.35),
    "coin_sound.mp3": int(MAX_VOLUME * 0.35),
    "skill_sound.mp3": MAX_VOLUME,
}

_opened = None
_chunks = {}  # 효과음 파일별 SDL chunk (여러 Sfx 인스턴스가 공유)


def _open():
    """오디오 장치를 한 번만 연다. 성공하면 True."""
    global _opened
    if _opened is None:
        try:
            mix.Mix_Init(mix.MIX_INIT_MP3)
            _opened = mix.Mix_OpenAudio(44100, mix.MIX_DEFAULT_FORMAT, 2, 2048) == 0
        except Exception:
            _opened = False
        if not _opened:
            print("[audio] 오디오 장치를 열 수 없습니다.")
    return _opened


def _close():
    global _opened
    if _opened:
        mix.Mix_CloseAudio()
    _opened = False


def _scaled(level, master):
    """파일별 음량에 마스터 음량/음소거를 적용한다."""
    if MUTED:
        return 0
    value = int(level * master / MAX_VOLUME)
    return max(0, min(MAX_VOLUME, value))


def music_volume():
    """현재 배경음악에 적용되는 실제 음량."""
    return _scaled(MUSIC_LEVEL, BGM_VOLUME)


def sfx_level(file_name=None):
    """현재 효과음에 적용되는 실제 음량."""
    base = SFX_VOLUMES.get(file_name, DEFAULT_SFX_LEVEL)
    return _scaled(base, SFX_VOLUME)


def percent(master):
    """슬라이드에 표시할 0~100 값."""
    return int(round(master * 100.0 / MAX_VOLUME))


def bgm_percent():
    return percent(BGM_VOLUME)


def sfx_percent():
    return percent(SFX_VOLUME)


def set_bgm_volume(value):
    """배경음악 음량을 0~MAX_VOLUME 으로 지정하고 바로 반영한다."""
    global BGM_VOLUME
    BGM_VOLUME = max(0, min(MAX_VOLUME, int(value)))
    if _opened:
        mix.Mix_VolumeMusic(music_volume())


def change_bgm_volume(delta):
    set_bgm_volume(BGM_VOLUME + delta)


def set_sfx_volume(value):
    """효과음 음량을 0~MAX_VOLUME 으로 지정한다."""
    global SFX_VOLUME
    SFX_VOLUME = max(0, min(MAX_VOLUME, int(value)))


def change_sfx_volume(delta):
    set_sfx_volume(SFX_VOLUME + delta)


def set_muted(value):
    """전체 음소거를 켜거나 끄고, 재생 중인 소리에도 바로 반영한다."""
    global MUTED
    MUTED = bool(value)
    if _opened:
        mix.Mix_VolumeMusic(music_volume())
    apply_sfx_volumes()


def toggle_muted():
    set_muted(not MUTED)


def is_muted():
    return MUTED


def apply_sfx_volumes():
    """이미 읽어 둔 효과음의 음량도 옵션 값에 맞춰 다시 설정한다."""
    if not _opened:
        return
    for name, chunk in _chunks.items():
        mix.Mix_VolumeChunk(chunk, sfx_level(name))


class Bgm:
    def __init__(self):
        self.music = None
        self.path = None

    @property
    def ok(self):
        return bool(_open())

    def play(self, file_name):
        """sound 폴더의 file_name 을 반복 재생한다. 같은 곡이면 그대로 둔다."""
        if not self.ok:
            return
        path = os.path.join(SOUND_DIR, file_name)
        if path == self.path:
            return
        self._free()
        music = mix.Mix_LoadMUS(path.encode("utf-8"))
        if not music:
            print("[audio] 음악을 읽을 수 없습니다:", path)
            return
        self.music = music
        self.path = path
        mix.Mix_VolumeMusic(music_volume())
        mix.Mix_PlayMusic(music, -1)

    def pause(self):
        if self.ok:
            mix.Mix_PauseMusic()

    def resume(self):
        if self.ok:
            mix.Mix_ResumeMusic()

    def _free(self):
        if self.music:
            mix.Mix_HaltMusic()
            mix.Mix_FreeMusic(self.music)
            self.music = None
            self.path = None

    def close(self):
        self._free()
        _close()


class Sfx:
    def __init__(self):
        self.chunks = _chunks

    def play(self, file_name, volume=None):
        """효과음을 재생한다. volume(0~1)을 주면 파일별 음량 대신 그 값을 쓴다."""
        if not _open():
            return
        chunk = self.chunks.get(file_name)
        if chunk is None:
            path = os.path.join(SOUND_DIR, file_name)
            chunk = mix.Mix_LoadWAV(path.encode("utf-8"))
            if not chunk:
                print("[audio] 효과음을 읽을 수 없습니다:", path)
                return
            self.chunks[file_name] = chunk
        if volume is None:
            level = sfx_level(file_name)
        else:
            level = _scaled(int(MAX_VOLUME * volume), SFX_VOLUME)
        mix.Mix_VolumeChunk(chunk, level)
        mix.Mix_PlayChannel(-1, chunk, 0)
