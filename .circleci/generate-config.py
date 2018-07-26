#!/usr/bin/env python3


def generate(cci):
    cci.job(
        "build", image="circleci/python:3.7-stretch", cache=["~/.cargo", "./target"]
    ).run(
        "Install dependencies",
        """
        sudo apt update
        sudo apt install build-essential -y
        """,
    ).run(
        "Install rust",
        """
        curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain nightly
        echo 'export PATH=${HOME}/.cargo/bin:${PATH}' >> $BASH_ENV
        source $BASH_ENV
        rustup update
        rustup install nightly
        rustup default nightly
        rustup component add rustfmt-preview
        """,
    ).run(
        "Install Poetry",
        "curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | sudo python3.7",
    ).run(
        "Install Package", "poetry install -v"
    ).run(
        "Check Rust Formatting", "rustup run nightly cargo fmt -- --check"
    ).run(
        "Check Python Formatting",
        "poetry run black --check src tests build.py .circleci tools",
    ).run(
        "Build Debug",
        """
        cc --version
        rustup run nightly cargo build
        """,
    ).run(
        "Build Release", "rustup run nightly cargo build --release"
    ).run(
        "Run Rust Tests", "rustup run nightly cargo test"
    ).run(
        "Run Python Tests", "poetry run pytest"
    ).finalize()


import json
from pathlib import Path
from typing import *

import attr


@attr.s(auto_attribs=True)
class Job:
    cci: "CCI"
    name: str
    image: str
    cache: Optional[List[str]] = None

    @property
    def config(self):
        return self.cci.config["jobs"][self.name]

    @config.setter
    def config(self, value):
        self.cci.config["jobs"][self.name] = value

    def __attrs_post_init__(self):
        self.config = {"docker": [{"image": self.image}], "steps": ["checkout"]}
        if self.cache is not None:
            self.config["steps"].append({"restore_cache": {"key": "project-cache"}})

    def run(self, name: str, command: str) -> "Job":
        self.config["steps"].append({"run": {"name": name, "command": command}})
        return self

    def finalize(self):
        if self.cache is not None:
            self.config["steps"].append(
                {"save_cache": {"key": "project-cache", "paths": self.cache}}
            )


class CCI:
    def __init__(self):
        self.config = {"version": 2, "jobs": {}}

    def job(self, name: str, *, image: str, cache: Optional[List[str]] = None) -> Job:
        return Job(self, name, image, cache)


def main():
    cci = CCI()
    generate(cci)
    with (Path(__file__).parent / "config.yml").open("w") as fobj:
        json.dump(cci.config, fobj, indent=2)


if __name__ == "__main__":
    main()
