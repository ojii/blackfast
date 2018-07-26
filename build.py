import hashlib
import json
import stat
import sys
from base64 import urlsafe_b64encode
from functools import partial
from pathlib import Path
from subprocess import check_call, DEVNULL
from zipfile import ZipFile, ZipInfo

import click
from poetry.masonry.utils.tags import get_platform
from poetry.utils.helpers import normalize_version
from pytoml import load


def patch_wheel(version: str) -> Path:
    src_path = Path.cwd() / "dist" / f"blackfast-{version}-py3-none-any.whl"
    wheel_name = f"blackfast-{version}-py3-none-{get_platform().replace('.', '_').replace('-', '_')}.whl"
    dst_path = Path.cwd() / "dist" / wheel_name
    name = "blackfast.exe" if sys.platform == "win32" else "blackfast"
    with ZipFile(src_path, "r") as src, ZipFile(dst_path, "w") as dst:
        binary = Path.cwd() / "target" / "release" / name
        arcname = f"blackfast-{version}.data/scripts/{name}"
        zinfo = ZipInfo.from_file(binary, arcname)
        zinfo.external_attr |= stat.S_IXUSR
        with binary.open("rb") as fobj:
            data = fobj.read()
            size = len(data)
            hash_digest = (
                urlsafe_b64encode(hashlib.sha256(data).digest())
                .decode("ascii")
                .rstrip("=")
            )
            dst.writestr(zinfo, data)
            record = "{},sha256={},{}\n".format(arcname, hash_digest, size).encode(
                "utf-8"
            )
        record_path = f"blackfast-{version}.dist-info/RECORD"
        for info in src.infolist():
            if info.filename == record_path:
                records = record + src.read(info.filename)
                info.file_size = len(records)
                dst.writestr(info, records)
            else:
                dst.writestr(info, src.read(info.filename))
    src_path.unlink()
    return dst_path


@click.command()
@click.option("-j", "--json-output", is_flag=True, default=False)
def main(json_output: bool) -> None:
    if json_output:
        call = partial(check_call, stdout=DEVNULL)
    else:
        call = check_call
    call(["poetry", "build", "-f", "wheel"])
    with open("pyproject.toml") as fobj:
        config = load(fobj)
        version = normalize_version(config["tool"]["poetry"]["version"])
    call(["cargo", "build", "--release"])
    path = patch_wheel(version)
    if json_output:
        print(json.dumps({"version": version, "path": str(path)}))
    else:
        print("Done ✨")


if __name__ == "__main__":
    main()
