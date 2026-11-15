"""스테이지 데이터 구조.

스테이지마다 땅 구간, 체크포인트, 적, 가구(벤치/상자), 코인, 회복 아이템의 배치를 담는다.
실제 생성은 main.py 의 World 가 이 데이터를 읽어서 한다.
"""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class StageSpec:
    name: str
    world_w: int  # 월드 전체 가로 길이(카메라 이동 범위)
    goal_x: float  # 도착 지점 x
    segments: tuple  # 땅 구간 (left, right)
    checkpoints: tuple  # 체크포인트 x
    coin_lines: tuple  # 고정 코인 줄 (x1, x2, y)
    ground_bears: tuple  # 땅 위의 곰 (x, left, right)
    birds: tuple  # 날아다니는 새 (x, y)
    surface_bears: int  # 벤치/상자 윗면에 올라갈 곰 수
    bench_count: int
    box_count: int
    furniture_min_x: float
    furniture_max_x: float
    coin_total: int  # 랜덤 배치 코인 포함 전체 코인 수
    heart_count: int  # 회복 아이템 수
    heart_min_segment: int  # 회복 아이템이 나오기 시작하는 땅 번호(0부터)
    pit_arc_count: int  # 코인 포물선을 놓을 구멍 수
    time_bonus: int = 3000  # 클리어 시간 보너스의 기준 점수(시간이 지나면 줄어든다)
    # 배경/도로/울타리 그림 (sprites/object 안의 파일 이름)
    background: str = "background.png"
    background_overlay: str = "background_black.png"
    road: str = "road.png"
    fence: str = "fence2.png"
    bench_file: str = "bench.png"  # sprites/object 안의 벤치 그림
    box_file: str = "box2.png"  # sprites/object 안의 상자 그림


def repeat(spec, times, name):
    """스테이지 하나를 가로로 times 번 이어 붙인 스테이지를 만든다.

    한 번의 길이는 땅 구간의 오른쪽 끝(마지막 땅)으로 잡는다.
    개수(적, 코인, 아이템, 벤치, 상자)는 모두 times 배가 된다.
    """
    tile = spec.segments[-1][1]

    def shift(x, k):
        return x + k * tile

    segments = tuple((shift(l, k), shift(r, k))
                     for k in range(times) for l, r in spec.segments)
    checkpoints = tuple(shift(x, k) for k in range(times) for x in spec.checkpoints)
    coin_lines = tuple((shift(x1, k), shift(x2, k), y)
                       for k in range(times) for x1, x2, y in spec.coin_lines)
    ground_bears = tuple((shift(x, k), shift(l, k), shift(r, k))
                         for k in range(times) for x, l, r in spec.ground_bears)
    birds = tuple((shift(x, k), y) for k in range(times) for x, y in spec.birds)
    last = times - 1
    return replace(
        spec,
        name=name,
        world_w=last * tile + spec.world_w,
        goal_x=last * tile + spec.goal_x,
        segments=segments,
        checkpoints=checkpoints,
        coin_lines=coin_lines,
        ground_bears=ground_bears,
        birds=birds,
        surface_bears=spec.surface_bears * times,
        bench_count=spec.bench_count * times,
        box_count=spec.box_count * times,
        furniture_max_x=last * tile + spec.furniture_max_x,
        coin_total=spec.coin_total * times,
        heart_count=spec.heart_count * times,
        pit_arc_count=spec.pit_arc_count * times,
    )
