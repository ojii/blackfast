import asyncio
import logging
import sys
from pathlib import Path
from typing import Awaitable, Callable, Union

PathLike = Union[Path, str]
Callback = Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]


async def run(unix_path: PathLike, windows_name: str, callback: Callback) -> None:
    name = windows_name if sys.platform == "win32" else str(unix_path)
    server = await start_server(callback, name)
    logging.info(f"Running at {name}")
    await server.serve_forever()


if sys.platform == "win32":

    async def start_server(callback: Callback, name: str) -> asyncio.AbstractServer:
        def factory() -> asyncio.StreamReaderProtocol:
            return asyncio.StreamReaderProtocol(asyncio.StreamReader(), callback)

        server, *_ = await asyncio.get_event_loop().start_serving_pipe(
            factory, address=f"\\\\.\\pipe\\{name}"
        )
        return server


else:
    start_server = asyncio.start_unix_server
