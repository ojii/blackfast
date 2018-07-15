# Experiment to make black faster

This is experimental. It will probably not work on most platforms. Everything needs to be done manually.

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
- [?] Manage starting/running the server automatically. Running `blackfast` should start the server if not running or use an already running one. 
- [x] Move the socket to a "well known" location (appdirs?cachedir?) so it doesn't need to be provided. This needs to work with more than one black version on a single system.
- [x] Make it installable (how to handle the rust part?!)
- [ ] Handle errors
- [ ] Add support for styled output
- [ ] Eventually: Don't read/write the cache on each request.
