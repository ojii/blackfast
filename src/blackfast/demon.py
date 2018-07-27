import atexit
import os
import signal
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from types import FunctionType
from typing import Optional


class PidExists(Exception):
    pass


class PidDoesNotExist(Exception):
    pass


def spawn(
    pid_file: Path,
    func: FunctionType,
    stdout_path: Optional[Path] = None,
    stderr_path: Optional[Path] = None,
):
    kwargs = {}
    try:
        # windows
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        exe = str(Path(sys.executable).parent / "pythonw.exe")
    except AttributeError:
        exe = sys.executable
    try:
        with pid_file.open("x") as fobj:
            process = subprocess.Popen(
                [exe, __file__, str(pid_file), func.__module__, func.__name__],
                stdout=stdout_path and stdout_path.open("w") or subprocess.DEVNULL,
                stderr=stderr_path and stderr_path.open("w") or subprocess.DEVNULL,
                **kwargs
            )
            fobj.write(str(process.pid))
    except FileExistsError:
        raise PidExists()


def kill(pid_path: Path):
    try:
        with pid_path.open("r") as fobj:
            pid = fobj.read()
            os.kill(int(pid), signal.SIGINT)
    except FileNotFoundError:
        raise PidDoesNotExist()


def run_child(pid_path: str, module: str, func: str) -> None:
    atexit.register(os.unlink, pid_path)
    getattr(import_module(module), func)()


if __name__ == "__main__":
    run_child(*sys.argv[1:])
