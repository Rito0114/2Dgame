"""배경음악과 효과음 재생 (SDL_mixer).

- Bgm: 배경음악. 한 번에 한 곡만 반복 재생하고, 스테이지가 바뀌면 곡을 바꾼다.
- Sfx: 효과음. 짧은 소리를 겹쳐서 재생한다.

오디오 장치를 열 수 없으면 아무것도 재생하지 않는다.
"""

import os

import sdl2.sdlmixer as mix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, "sound")
BGM_VOLUME = int(mix.MIX_MAX_VOLUME * 0.35)
SFX_VOLUME = int(mix.MIX_MAX_VOLUME * 0.7)
# 파일별 효과음 음량(기본값은 SFX_VOLUME). 음량은 최대치(MIX_MAX_VOLUME)를 넘을 수 없다.
SFX_VOLUMES = {
    "falling_sound.mp3": mix.MIX_MAX_VOLUME,
    "checkpoint_sound.mp3": mix.MIX_MAX_VOLUME,
    "jump_sound.mp3": mix.MIX_MAX_VOLUME,
    "heal_sound.mp3": int(mix.MIX_MAX_VOLUME * 0.35),
    "coin_sound.mp3": int(mix.MIX_MAX_VOLUME * 0.35),
}

_opened = None


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
        mix.Mix_VolumeMusic(BGM_VOLUME)
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
        self.chunks = {}

    def play(self, file_name):
        if not _open():
            return
        chunk = self.chunks.get(file_name)
        if chunk is None:
            path = os.path.join(SOUND_DIR, file_name)
            chunk = mix.Mix_LoadWAV(path.encode("utf-8"))
            if not chunk:
                print("[audio] 효과음을 읽을 수 없습니다:", path)
                return
            mix.Mix_VolumeChunk(chunk, SFX_VOLUMES.get(file_name, SFX_VOLUME))
            self.chunks[file_name] = chunk
        mix.Mix_PlayChannel(-1, chunk, 0)
