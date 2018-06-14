# Experiment to make black faster

This is experimental. It will probably not work on most platforms. Everything needs to be done manually.

## What/Why

This rather silly implementation speeds up the runtime of [black](https://github.com/ambv/black) by up to 10x in some of my tests.

Running black on (an already formatted, cached) server.py in this repository takes ~170ms on my machine. Using blackfast it takes ~10ms.

Running black on the Python 3.7 standard library (unformatted, uncached) takes ~3m49s with black, ~3m34s with blackfast.

In other words, it helps for small amounts of works much more than if there's lots to do.

## How it works

Python startup is slow. So we don't start Python to use black, instead run a server which runs black and have a tiny rust cli program that communicates with that server.

## How to run this experiment

You'll need Python 3.7

1. Make sure black 18.6b2 is installed. 
2. Run `python server.py <path-to-socket>`. 
3. Run `cargo build --release`
4. Run `target/release/blackfast <path-to-socket> <normal-args-you-would-pass-to-black>`

Alternatively for 3 and 4 you can use `cargo run <...args>`.

## What needs to be done for this to be useful?

- [ ] Make it work on Windows/any platform
- [ ] Manage starting/running the server automatically. Running `blackfast` should start the server if not running or use an already running one. 
- [ ] Move the socket to a "well known" location (appdirs?cachedir?) so it doesn't need to be provided. This needs to work with more than one black version on a single system.
- [ ] Make it installable (how to handle the rust part?!)
- [ ] Handle errors
- [ ] Add support for styled output
- [ ] Eventually: Don't read/write the cache on each request.
