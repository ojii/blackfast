#[macro_use]
extern crate serde_json;

use std::io::BufRead;
use std::io::Write;
use std::str;

use std::io::BufReader;
use std::os::unix::net::UnixStream;
use std::env;

extern crate byteorder;

use byteorder::{ReadBytesExt, LittleEndian};
use std::io::Cursor;


// TODO this should be trivial to optimize
macro_rules! get_retcode {
    ($a:expr, $b:expr, $c:expr, $d:expr) => {{
        Cursor::new(vec![$a, $b, $c, $d]).read_i32::<LittleEndian>().unwrap()
    }}
}

fn run() -> Result<(), i32> {
    let mut args = env::args().skip(1).collect::<Vec<String>>();
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
    stream.write_all(format!("{}\n", request).as_bytes()).unwrap();
    let mut reader = BufReader::new(stream);
    let mut buf: Vec<u8> = Vec::with_capacity(100);
    loop {
        match reader.read_until(b'\n', &mut buf) {
            Ok(i) if i == 0 => return Err(-1),
            Ok(_) => {
                match buf.as_slice() {
                    [0, a, b, c, d, b'\n'] => return Err(get_retcode!(*a, *b, *c, *d)),
                    slice => print!("{}", str::from_utf8(&slice).unwrap()),
                }
            }
            Err(err) => eprintln!("{}", err),
        }
        buf.clear();
    }
}

fn main() {

    ::std::process::exit(match run() {
       Ok(_) => 0,
       Err(retcode) => retcode
    });
}
