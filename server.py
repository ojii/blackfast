import asyncio
import json
import re
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from contextvars import ContextVar
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import *

import black
import click

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


# Monkeypatching :(
out = black.out = partial(context_out, original=black.out)
err = black.err = partial(context_out, original=black.err)
secho = partial(context_out, original=click.secho)


@click.command()
@click.argument("socket_path")
def main(socket_path: str) -> None:
    asyncio.run(server(socket_path))


async def server(socket_path: str) -> None:
    srv = await asyncio.start_unix_server(connected, socket_path)
    async with srv:
        await srv.serve_forever()


async def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    STDOUT.set(writer)
    try:
        data = json.loads(await reader.readline())
    except asyncio.IncompleteReadError:
        return writer.close()
    return_code = await api(**data)
    writer.write(b"\x00")
    writer.write(struct.pack("b", return_code))
    writer.write(b"\n")
    await writer.drain()
    writer.close()


async def api(
    *,
    src: Iterable[str],
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
    loop = asyncio.get_event_loop()
    write_back = black.WriteBack.from_configuration(check=check, diff=diff)
    mode = black.FileMode.from_configuration(
        py36=py36, pyi=pyi, skip_string_normalization=skip_string_normalization
    )
    if config and verbose:
        out(f"Using configuration from {config}.", bold=False, fg="blue")
    try:
        include_regex = black.re_compile_maybe_verbose(include)
    except re.error:
        err(f"Invalid regular expression for include given: {include!r}")
        return 2
    try:
        exclude_regex = black.re_compile_maybe_verbose(exclude)
    except re.error:
        err(f"Invalid regular expression for exclude given: {exclude!r}")
        return 2
    report = black.Report(check=check, quiet=quiet, verbose=verbose)
    root = black.find_project_root(src)
    sources: Set[Path] = set()
    for s in src:
        p = Path(s)
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
            err(f"invalid path: {s}")
    if len(sources) == 0:
        if verbose or not quiet:
            out("No paths given. Nothing to do 😴")
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
        out(f"All done! {bang}")
        secho(str(report), err=True)
    return report.return_code


if __name__ == "__main__":
    main()
