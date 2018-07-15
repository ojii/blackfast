import hashlib
import stat
from base64 import urlsafe_b64encode
from pathlib import Path
from subprocess import check_call
from zipfile import ZipFile, ZipInfo

from poetry.masonry.utils.tags import get_platform
from poetry.utils.helpers import normalize_version
from pytoml import load


def foo():
    zin = zipfile.ZipFile("archive.zip", "r")
    zout = zipfile.ZipFile("archve_new.zip", "w")
    for item in zin.infolist():
        buffer = zin.read(item.filename)
        if item.filename[-4:] != ".exe":
            zout.writestr(item, buffer)
    zout.close()
    zin.close()


def patch_wheel(version: str):
    src_path = Path.cwd() / "dist" / f"blackfast-{version}-py3-none-any.whl"
    wheel_name = f"blackfast-{version}-py3-none-{get_platform().replace('.', '_').replace('-', '_')}.whl"
    dst_path = Path.cwd() / "dist" / wheel_name
    with ZipFile(src_path, "r") as src, ZipFile(dst_path, "w") as dst:
        binary = Path.cwd() / "target" / "release" / "blackfast"
        arcname = f"blackfast-{version}.data/scripts/blackfast"
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


def main():
    check_call(["poetry", "build", "-f", "wheel"])
    with open("pyproject.toml") as fobj:
        config = load(fobj)
        version = normalize_version(config["tool"]["poetry"]["version"])
    check_call(["cargo", "build", "--release"])
    patch_wheel(version)
    print("Done ✨")


if __name__ == "__main__":
    main()
