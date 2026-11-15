"""배경음악 재생 (SDL_mixer).

한 번에 한 곡만 반복 재생한다. 스테이지가 바뀌면 곡을 바꾼다.
오디오 장치를 열 수 없으면 조용히 아무것도 하지 않는다.
"""

import os

import sdl2
import sdl2.sdlmixer as mix

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, "sound")
VOLUME = int(mix.MIX_MAX_VOLUME * 0.35)


class Bgm:
    def __init__(self):
        self.music = None
        self.path = None
        self.ok = False
        try:
            mix.Mix_Init(mix.MIX_INIT_MP3)
            self.ok = mix.Mix_OpenAudio(44100, mix.MIX_DEFAULT_FORMAT, 2, 2048) == 0
        except Exception:
            self.ok = False
        if not self.ok:
            print("[audio] 오디오 장치를 열 수 없습니다.")

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
        mix.Mix_VolumeMusic(VOLUME)
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
        if self.ok:
            self._free()
            mix.Mix_CloseAudio()
            self.ok = False
