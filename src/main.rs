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
use std::io::Read;
#[cfg(not(windows))]
use std::os::unix::net::UnixStream;
use std::path::PathBuf;
use std::process::Command;

#[cfg(windows)]
const DEFAULT_PIPE_NAME: &'static str = "\\\\.\\pipe\\blackfast";

#[cfg(windows)]
const SERVER_BIN_NAME: &'static str = "blackfast-server.exe";

#[cfg(not(windows))]
const SERVER_BIN_NAME: &'static str = "blackfast-server";

#[inline]
fn get_retcode(a: u8, b: u8, c: u8, d: u8) -> i32 {
    let mut number = u32::from(d);
    number = number << 8 | u32::from(c);
    number = number << 8 | u32::from(b);
    number = number << 8 | u32::from(a);
    number as i32
}

fn user_data_dir(filename: String) -> Result<PathBuf, ()> {
    appdirs::user_data_dir(Some("blackfast"), None, false).map(|p| p.join(filename))
}

fn get_env_or_user_data_dir(name: &str, ext: &str) -> Result<PathBuf, ()> {
    match env::var(format!("{}_{}", name.to_uppercase(), ext.to_uppercase())) {
        Ok(val) => Ok(PathBuf::from(val)),
        Err(_) => user_data_dir(format!("{}.{}", name, ext)),
    }
}

#[cfg(not(windows))]
fn get_socket() -> Result<PathBuf, ()> {
    get_env_or_user_data_dir("blackfast", "socket")
}

fn get_pidfile() -> Result<PathBuf, ()> {
    get_env_or_user_data_dir("blackfast", "pid")
}

#[cfg(windows)]
fn get_pipe_name() -> String {
    match env::var("BLACKFAST_PIPE_NAME") {
        Ok(name) => name,
        Err(_) => String::from(DEFAULT_PIPE_NAME),
    }
}

fn maybe_start(p: &PathBuf) {
    if !p.exists() {
        Command::new(SERVER_BIN_NAME)
            .arg("start")
            .spawn()
            .expect("failed to start server")
            .wait()
            .expect("failed to start server");
    }
}

#[cfg(not(windows))]
fn connect() -> Result<impl Read + Write, ()> {
    let socket = match get_socket() {
        Ok(p) => p,
        Err(_) => return Err(()),
    };
    match UnixStream::connect(socket) {
        Ok(sock) => Ok(sock),
        Err(_) => Err(()),
    }
}

#[cfg(windows)]
fn connect() -> Result<impl Read + Write, ()> {
    match File::open(get_pipe_name()) {
        Ok(f) => Ok(f),
        Err(_) => return Err(()),
    }
}

fn run() -> Result<(), i32> {
    let pidfile = match get_pidfile() {
        Ok(p) => p,
        Err(_) => return Err(-1),
    };
    maybe_start(&pidfile);
    let mut args: Vec<String> = env::args().skip(1).collect();
    let mut full_args: Vec<String> = Vec::with_capacity(args.len() + 2);
    full_args.push(String::from("--work-dir"));
    full_args.push(String::from(env::current_dir().unwrap().to_str().unwrap()));
    full_args.append(&mut args);
    let request = json!(full_args);
    let mut stream = match connect() {
        Ok(stream) => stream,
        Err(_) => match std::fs::remove_file(&pidfile) {
            Ok(_) => {
                maybe_start(&pidfile);
                match connect() {
                    Ok(stream) => stream,
                    Err(_) => return Err(-1),
                }
            }
            Err(_) => return Err(-1),
        },
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
