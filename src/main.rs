#[macro_use]
extern crate serde_json;
extern crate appdirs;

use std::io::BufRead;
use std::io::Write;
use std::str;

use std::env;
#[cfg(windows)]
use std::fs::File;
use std::io::BufReader;
#[cfg(not(windows))]
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::Command;

#[cfg(windows)]
const PIPE_NAME: &'static str = "\\\\.\\pipe\\blackfast";

#[inline]
fn get_retcode(a: u8, b: u8, c: u8, d: u8) -> i32 {
    let mut number = u32::from(d);
    number = number << 8 | u32::from(c);
    number = number << 8 | u32::from(b);
    number = number << 8 | u32::from(a);
    number as i32
}

fn user_data_dir(filename: &str) -> Result<PathBuf, ()> {
    appdirs::user_data_dir(Some("blackfast"), None, false).map(|p| p.join(filename))
}

fn get_socket() -> Result<PathBuf, ()> {
    user_data_dir("blackfast.socket")
}

fn get_pidfile() -> Result<PathBuf, ()> {
    user_data_dir("blackfast.pid")
}

fn maybe_start(p: &PathBuf) {
    if !p.exists() {
        Command::new("python")
            .arg("server.py")
            .arg("start")
            .spawn()
            .expect("failed to start server")
            .wait()
            .expect("failed to start server");
    }
}

fn run() -> Result<(), i32> {
    match get_pidfile() {
        Ok(p) => maybe_start(&p),
        Err(_) => return Err(-1),
    }
    let mut args: Vec<String> = env::args().skip(1).collect();
    let mut full_args: Vec<String> = Vec::with_capacity(args.len() + 2);
    full_args.push(String::from("--work-dir"));
    full_args.push(String::from(env::current_dir().unwrap().to_str().unwrap()));
    full_args.append(&mut args);
    let request = json!(full_args);

    #[cfg(not(windows))]
    let socket = match get_socket() {
        Ok(p) => p,
        Err(_) => return Err(-1),
    };
    #[cfg(not(windows))]
    let mut stream = match UnixStream::connect(socket) {
        Ok(sock) => sock,
        Err(err) => {
            eprintln!("{}", err);
            return Err(-1);
        }
    };
    #[cfg(windows)]
    let mut stream = match File::open(PIPE_NAME) {
        Ok(f) => f,
        Err(err) => return Err(-1),
    };

    stream
        .write_all(format!("{}\n", request).as_bytes())
        .unwrap();
    let mut reader = BufReader::new(stream);
    let mut buf: Vec<u8> = Vec::with_capacity(100);
    loop {
        match reader.read_until(b'\n', &mut buf) {
            Ok(i) if i == 0 => return Err(-1),
            Ok(_) => match buf.as_slice() {
                [0, a, b, c, d, b'\n'] => return Err(get_retcode(*a, *b, *c, *d)),
                slice => print!("{}", str::from_utf8(&slice).unwrap()),
            },
            Err(err) => eprintln!("{}", err),
        }
        buf.clear();
    }
}

fn main() {
    ::std::process::exit(match run() {
        Ok(_) => 0,
        Err(retcode) => retcode,
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_retcode() {
        assert_eq!(get_retcode(255, 255, 255, 255), -1);
        assert_eq!(get_retcode(254, 255, 255, 255), -2);
        assert_eq!(get_retcode(10, 0, 0, 0), 10);
    }
}
