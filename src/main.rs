#[macro_use]
extern crate serde_json;

use std::io::BufRead;
use std::io::Write;
use std::str;

use std::env;
use std::io::BufReader;
use std::os::unix::net::UnixStream;

#[inline]
fn get_retcode(a: &u8, b: &u8, c: &u8, d: &u8) -> i32 {
    let mut number: u32 = *d as u32;
    number = number << 8 | *c as u32;
    number = number << 8 | *b as u32;
    number = number << 8 | *a as u32;
    number as i32
}

fn run() -> Result<(), i32> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    let mut full_args: Vec<String> = Vec::with_capacity(args.len() + 2);
    full_args.push(String::from("--work-dir"));
    full_args.push(String::from(env::current_dir().unwrap().to_str().unwrap()));
    full_args.append(&mut args);
    let request = json!(full_args);
    let mut stream = match UnixStream::connect("blackfast.socket") {
        Ok(sock) => sock,
        Err(err) => {
            eprintln!("{}", err);
            return Err(-1);
        }
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
                [0, a, b, c, d, b'\n'] => return Err(get_retcode(a, b, c, d)),
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
        assert_eq!(get_retcode(&255, &255, &255, &255), -1);
        assert_eq!(get_retcode(&254, &255, &255, &255), -2);
        assert_eq!(get_retcode(&10, &0, &0, &0), 10);
    }
}
