[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Python Version:3.7](https://img.shields.io/badge/Python-3.7-brightgreen.svg)](https://www.python.org/)
[![Packaging:poetry](https://img.shields.io/badge/Packaging-poetry-brightgreen.svg)](https://poetry.eustace.io/)
[![Rust:Nightly](https://img.shields.io/badge/Rust-Nightly-brightgreen.svg)](https://www.rust-lang.org/)

# blackfast

Make [black](https://github.com/ambv/black) faster, with rust. 

# Build Status

| OS | Status |
| --- | --- |
| Linux | [![CircleCI](https://circleci.com/gh/ojii/blackfast.svg?style=svg)](https://circleci.com/gh/ojii/blackfast) |
| MacOS | [![Build Status](https://travis-ci.com/ojii/blackfast.svg?branch=master)](https://travis-ci.com/ojii/blackfast) |
| Windows | [![Build status](https://ci.appveyor.com/api/projects/status/0wedeehfetvi7fef/branch/master?svg=true)](https://ci.appveyor.com/project/ojii/blackfast/branch/master) |

## Benchmarks

These are generated with `tools/benchmark.py`. 


```text
name                        mean    median    stdev
-----------------------  -------  --------  -------
black_cached             0.17876   0.18076  0.00433
black_uncached           0.17931   0.17946  0.00514
blackfast_cached_cold    0.89011   0.86907  0.03016
blackfast_uncached_cold  0.92398   0.93126  0.04577
blackfast_cached_hot     0.04327   0.04298  0.00097
blackfast_uncached_hot   0.04538   0.04424  0.00365
```

## How it works

Python startup is slow. So we don't start Python to use black, instead run a server which runs black and have a tiny rust cli program that communicates with that server.

## How to run this experiment

You'll need Python 3.7, poetry and rust nightly.

1. Run `poetry install` or `poetry develop`.
3. Run `cargo build --release`
4. Run `target/release/blackfast <normal-args-you-would-pass-to-black>`

Alternatively for 3 and 4 you can use `cargo run <...args>`.

## How to build a wheel

1. Run `python build.py`

## What needs to be done for this to be useful?

- [?] Make it work on Windows/any platform (Maybe done?)
- [x] Manage starting/running the server automatically. Running `blackfast` should start the server if not running or use an already running one. 
- [x] Move the socket to a "well known" location (appdirs?cachedir?) so it doesn't need to be provided. This needs to work with more than one black version on a single system.
- [ ] support multiple versions to be installed/used
- [x] Make it installable (how to handle the rust part?!)
- [ ] Handle errors
- [ ] Add support for styled output
- [ ] Eventually: Don't read/write the cache on each request.
