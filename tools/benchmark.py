import os
import statistics
import time
from subprocess import call, DEVNULL
from typing import Callable, List, Tuple, Iterable, Union
import black
import click
import tabulate

BLACKFAST = os.path.join(
    os.path.dirname(__file__), "..", "target", "release", "blackfast"
)


def _black() -> float:
    start = time.monotonic()
    call(["black", __file__], stderr=DEVNULL, stdout=DEVNULL, stdin=DEVNULL)
    end = time.monotonic()
    return end - start


def _uncache():
    cache = black.get_cache_file(black.DEFAULT_LINE_LENGTH, black.FileMode.AUTO_DETECT)
    if cache.exists():
        cache.unlink()


def _start():
    call(["blackfast-server", "start"], stderr=DEVNULL, stdout=DEVNULL, stdin=DEVNULL)


def _stop():
    call(["blackfast-server", "stop"], stderr=DEVNULL, stdout=DEVNULL, stdin=DEVNULL)


def _blackfast():
    start = time.monotonic()
    call([BLACKFAST, __file__], stderr=DEVNULL, stdout=DEVNULL, stdin=DEVNULL)
    end = time.monotonic()
    return end - start


def black_cached() -> float:
    _black()
    return _black()


def black_uncached() -> float:
    _uncache()
    return _black()


def blackfast_cached_cold() -> float:
    _stop()
    _black()
    return _blackfast()


def blackfast_uncached_cold() -> float:
    _stop()
    _uncache()
    return _blackfast()


def blackfast_cached_hot() -> float:
    _start()
    _blackfast()
    return _blackfast()


def blackfast_uncached_hot() -> float:
    _start()
    _uncache()
    return _blackfast()


Benchmark = Callable[[], float]
BENCHMARKS: List[Benchmark] = [
    black_cached,
    black_uncached,
    blackfast_cached_cold,
    blackfast_uncached_cold,
    blackfast_cached_hot,
    blackfast_uncached_hot,
]


def run(iterations: int) -> Iterable[Tuple[str, List[float]]]:
    return (
        (bench.__name__, [bench() for _ in range(iterations)]) for bench in BENCHMARKS
    )


def analyze(runs: List[float]) -> Iterable[float]:
    yield statistics.mean(runs)
    yield statistics.median(runs)
    yield statistics.stdev(runs)


@click.command()
@click.option("-i", "--iterations", type=click.IntRange(0), default=25)
def main(iterations: int) -> None:
    headers = ["name", "mean", "median", "stdev"]
    data = [(name, *analyze(runs)) for name, runs in run(iterations)]
    print(tabulate.tabulate(data, headers, floatfmt=".5f"))


if __name__ == "__main__":
    main()
