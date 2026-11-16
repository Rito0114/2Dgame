"""2스테이지: 1스테이지를 가로로 3번 이어 붙인 맵.

길이, 몬스터 수, 코인 수, 회복 아이템 수, 벤치와 상자 수가 모두 1스테이지의 3배다.
"""

from dataclasses import replace

from stage import repeat
from stage1 import SPEC as STAGE1

SPEC = replace(
    repeat(STAGE1, times=3, name="2스테이지"),
    background="background_stage2.png",
    time_bonus=9000,
    bgm="stage2_bgm.mp3",
    bombs=True,
    # 고양이는 4번째 땅(세 번째 인덱스 땅 이후)부터 나온다.
    cats=(
        (4900, 4400, 5450),
        (9100, 8600, 9750),
        (13100, 12600, 13750),
        (17400, 16900, 17950),
    ),
    road="road_stage2.png",
    fence="fence_stage2.png",
    bench_file="bench_stage2.png",
    box_file="box_stage2.png",
)
