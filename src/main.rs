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


fn get_retcode(a: u8, b: u8, c: u8, d: u8) -> i32 {
  Cursor::new(vec![a, b, c, d]).read_i32::<LittleEndian>().unwrap()
}


fn main() {
  let request = json!(env::args().skip(1).collect::<Vec<String>>());
  let mut stream = match UnixStream::connect("blackfast.socket") {
    Ok(sock) => sock,
    Err(err) => {
      eprintln!("{}", err);
      ::std::process::exit(-1);
    }
  };
  stream.write_all(format!("{}\n", request).as_bytes()).unwrap();
  let mut reader = BufReader::new(stream);
  let mut buf: Vec<u8> = Vec::with_capacity(100);
  loop {
    match reader.read_until(b'\n', &mut buf) {
      Ok(i) if i == 0 => ::std::process::exit(-1),
      Ok(_) => {
        match buf.as_slice() {
          [0, a, b, c, d, b'\n'] => ::std::process::exit(get_retcode(*a, *b, *c, *d)),
          slice => print!("{}", str::from_utf8(&slice).unwrap()),
        }
      }
      Err(err) => eprintln!("{}", err),
    }
    buf.clear();
  }
}
