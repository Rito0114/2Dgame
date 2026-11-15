"""2스테이지: 1스테이지를 가로로 3번 이어 붙인 맵.

길이, 몬스터 수, 코인 수, 회복 아이템 수, 벤치와 상자 수가 모두 1스테이지의 3배다.
"""

from stage import repeat
from stage1 import SPEC as STAGE1

SPEC = repeat(STAGE1, times=3, name="2스테이지")
