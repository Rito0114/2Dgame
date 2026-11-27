"""3스테이지: 짧은 보스 전용 맵.

가로 1600px 짜리 한 구간뿐이다. 포탈/코인/회복 아이템은 없고,
큰 곰 보스를 쓰러뜨리면 즉시 스테이지가 클리어된다.
"""

from stage import StageSpec

SPEC = StageSpec(
    name="3스테이지",
    world_w=1600,
    goal_x=1500,
    segments=((0, 1600),),
    checkpoints=(),
    coin_lines=(),
    ground_bears=(),
    birds=(),
    surface_bears=0,
    bench_count=2,
    box_count=2,
    furniture_min_x=180,
    furniture_max_x=900,
    coin_total=0,
    heart_count=0,
    heart_min_segment=0,
    pit_arc_count=0,
    time_bonus=3000,
    bgm="stage2_bgm.mp3",
    dash=True,
    boss=True,
    portal=False,
    boss_x=1040,  # 오른쪽에서 걸어와 멈추는 지점 (화면 안쪽으로 더 왼쪽)
    boss_left=960,
    boss_right=1540,
    background="background_stage2.png",
    road="road_stage2.png",
    fence="fence_stage2.png",
    bench_file="bench_stage2.png",
    box_file="box_stage2.png",
)
