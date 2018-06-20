import asyncio
import json
import re
import socket
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from contextvars import ContextVar
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import *

import appdirs
import black
import click
import daemoniker

import ipcserver

p = lambda b, n: str((Path(b) / n).absolute())


def ensure(*paths: str) -> None:
    for path in paths:
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True)


dirs = appdirs.AppDirs("blackfast")
ensure(dirs.user_data_dir, dirs.user_log_dir)
STDOUT_LOG = p(dirs.user_log_dir, "stdout.log")
STDERR_LOG = p(dirs.user_log_dir, "stderr.log")
SOCKET_PATH = p(dirs.user_data_dir, "blackfast.socket")
PIPE_NAME = "blackfast"
PID_FILE = p(dirs.user_data_dir, "blackfast.pid")

PROCESS_POOL = ProcessPoolExecutor()

STDOUT = ContextVar("STDOUT", default=sys.stdout)


@dataclass
class ClickFile:
    stream: asyncio.StreamWriter

    def write(self, data: Union[bytes, str]):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.stream.write(data)

    def flush(self):
        pass


def context_out(*args, original, **kwargs):
    original(*args, **kwargs, file=ClickFile(STDOUT.get()))


def monkeypatch():
    black.out = partial(context_out, original=black.out)
    black.err = partial(context_out, original=black.err)
    black.secho = partial(context_out, original=click.secho)
    black.main = click.option("--work-dir", required=True)(black.main)
    for param in black.main.params:
        if param.name == "src":
            param.type.exists = False


async def server() -> None:
    await ipcserver.run(SOCKET_PATH, PIPE_NAME, connected)


async def send_return_code(writer: asyncio.StreamWriter, num: int) -> None:
    writer.write(b"\x00")
    writer.write(struct.pack("<i", num))
    writer.write(b"\n")
    await writer.drain()
    writer.close()


async def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    STDOUT.set(writer)
    try:
        args = json.loads(await reader.readline())
    except asyncio.IncompleteReadError:
        return writer.close()
    try:
        ctx = black.main.make_context("blackfast", args)
    except click.ClickException as exc:
        writer.write(f"{exc.format_message()}\n".encode("utf-8"))
        return await send_return_code(writer, -1)
    try:
        return_code = await api(**ctx.params)
    except Exception as e:
        writer.write(f"INTERNAL ERROR: {e}\n".encode("utf-8"))
        return await send_return_code(writer, -1)
    return await send_return_code(writer, return_code)


async def api(
    *,
    src: Iterable[str],
    work_dir: str,
    line_length: int = black.DEFAULT_LINE_LENGTH,
    check: bool = False,
    diff: bool = False,
    fast: bool = False,
    pyi: bool = False,
    py36: bool = False,
    skip_string_normalization: bool = False,
    quiet: bool = False,
    verbose: bool = False,
    include: str = black.DEFAULT_INCLUDES,
    exclude: str = black.DEFAULT_EXCLUDES,
    config: Optional[str] = None,
) -> int:
    """The uncompromising code formatter."""
    src = tuple(src)
    work_dir = Path(work_dir)
    loop = asyncio.get_event_loop()
    write_back = black.WriteBack.from_configuration(check=check, diff=diff)
    mode = black.FileMode.from_configuration(
        py36=py36, pyi=pyi, skip_string_normalization=skip_string_normalization
    )
    if config and verbose:
        black.out(f"Using configuration from {config}.", bold=False, fg="blue")
    try:
        include_regex = black.re_compile_maybe_verbose(include)
    except re.error:
        black.err(f"Invalid regular expression for include given: {include!r}")
        return 2
    try:
        exclude_regex = black.re_compile_maybe_verbose(exclude)
    except re.error:
        black.err(f"Invalid regular expression for exclude given: {exclude!r}")
        return 2
    report = black.Report(check=check, quiet=quiet, verbose=verbose)
    root = black.find_project_root((work_dir,))
    sources: Set[Path] = set()
    for s in src:
        p = work_dir / Path(s)
        if p.is_dir():
            sources.update(
                black.gen_python_files_in_dir(
                    p, root, include_regex, exclude_regex, report
                )
            )
        elif p.is_file() or s == "-":
            # if a file was explicitly given, we don't care about its extension
            sources.add(p)
        else:
            black.err(f"invalid path: {s}")
    if len(sources) == 0:
        if verbose or not quiet:
            black.out("No paths given. Nothing to do 😴")
        return 0

    if len(sources) == 1:
        black.reformat_one(
            src=sources.pop(),
            line_length=line_length,
            fast=fast,
            write_back=write_back,
            mode=mode,
            report=report,
        )
    else:
        await black.schedule_formatting(
            sources=sources,
            line_length=line_length,
            fast=fast,
            write_back=write_back,
            mode=mode,
            report=report,
            executor=PROCESS_POOL,
            loop=loop,
        )
    if verbose or not quiet:
        bang = "💥 💔 💥" if report.return_code else "✨ 🍰 ✨"
        black.out(f"All done! {bang}")
        black.secho(str(report), err=True)
    return report.return_code


def wait_connectable(timeout: Union[int, float]) -> None:
    end = time.monotonic() + timeout
    while end > time.monotonic():
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(SOCKET_PATH)
            sock.close()
            return
        except:
            pass
    raise Exception("Server did not start")


@click.group()
def cli() -> None:
    pass


@cli.command("start")
def start() -> None:
    with daemoniker.Daemonizer() as (_, daemonizer):
        is_parent, *_ = daemonizer(PID_FILE)
        if is_parent:
            wait_connectable(10)
    monkeypatch()
    asyncio.run(server())


@cli.command("stop")
def stop() -> None:
    daemoniker.send(PID_FILE, daemoniker.SIGINT)


if __name__ == "__main__":
    cli()
