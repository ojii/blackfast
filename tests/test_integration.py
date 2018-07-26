import json
import os
import secrets
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from subprocess import check_call, check_output
from types import ModuleType
from typing import Tuple

import pytest
from py._path.local import LocalPath


@pytest.fixture(scope="session")
def wheel(root: Path) -> Path:
    info = json.loads(
        check_output([sys.executable, str(root / "build.py"), "-j"], cwd=root)
    )
    return Path(info["path"])


@pytest.fixture
def socket_path() -> str:
    path = tempfile.mkdtemp()
    try:
        yield os.path.join(path, "blackfast.socket")
    finally:
        shutil.rmtree(path)


@dataclass
class Env:
    root: Path
    socket_path: str
    pipe_name: str = field(
        default_factory=lambda: f"\\\\.\\pipe\\{secrets.token_urlsafe(4)}"
    )
    pid_path: Path = field(init=False)

    def __post_init__(self):
        self.pid_path = self.root / f"blackfast.pid"

    def run(self, cmd: str, args: Tuple[str]):
        if sys.platform == "win32":
            cmd += ".exe"
        check_call(
            [str(self.root / "bin" / cmd), *args],
            env={
                **os.environ,
                "BLACKFAST_SOCKET": self.socket_path,
                "BLACKFAST_PID": str(self.pid_path),
                "BLACKFAST_PIPE_NAME": self.pipe_name,
            },
        )

    def pip(self, *args: str):
        self.run("pip", args)

    def blackfast(self, *args: str):
        self.run("blackfast", args)

    def blackfast_server(self, *args: str):
        self.run("blackfast-server", args)

    def black(self, *args: str):
        self.run("black", args)

    def make_file(self, contents: str) -> Path:
        name = f"{secrets.token_urlsafe()}.py"
        path = self.root / name
        with path.open("w") as fobj:
            fobj.write(contents)
        return path

    def copy_module(self, mod: ModuleType) -> Path:
        with Path(mod.__file__).open("r") as fobj:
            return self.make_file(fobj.read())


@pytest.fixture
def env(wheel: Path, tmpdir: LocalPath, socket_path: str) -> Env:
    root = Path(tmpdir) / "env"
    check_call([sys.executable, "-m", "venv", str(root)])
    venv = Env(root, socket_path)
    venv.pip("install", "-U", "pip")
    venv.pip("install", str(wheel))
    return venv


def test_blackfast_v_black(env):
    target = env.copy_module(secrets)
    control = env.copy_module(secrets)
    env.black(str(control))
    env.blackfast(str(target))
    with target.open("rb") as t, control.open("rb") as c:
        assert t.read() == c.read()
