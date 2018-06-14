extern crate clap;
#[macro_use]
extern crate serde_derive;
extern crate serde_json;

use std::io::BufRead;
use std::io::Write;

use clap::App;
use clap::Arg;
use std::io::BufReader;
use std::os::unix::net::UnixStream;
use std::path::Path;

const VERSION: &'static str = env!("CARGO_PKG_VERSION");
const AUTHORS: &'static str = env!("CARGO_PKG_AUTHORS");

const DEFAULT_EXCLUDES: &'static str =
    (r"/(\.git|\.hg|\.mypy_cache|\.tox|\.venv|_build|buck-out|build|dist)/");
const DEFAULT_INCLUDES: &'static str = r"\.pyi?$";

fn path_exists(v: String) -> Result<(), String> {
    let path = Path::new(&v);
    if path.exists() {
        Ok(())
    } else {
        Err(format!("Socket {} does not exist", v))
    }
}

#[derive(Serialize, Debug)]
struct Options<'a> {
    line_length: u8,
    check: bool,
    diff: bool,
    fast: bool,
    pyi: bool,
    py36: bool,
    skip_string_normalization: bool,
    quiet: bool,
    verbose: bool,
    include: &'a str,
    exclude: &'a str,
    src: Vec<&'a str>,
    config: Option<&'a str>,
}

fn main() {
    let app = App::new("blackfast")
        .version(VERSION)
        .author(AUTHORS)
        .about("Fast black")
        .arg(
            Arg::with_name("socket")
                .required(true)
                .validator(path_exists),
        )
        .arg(
            Arg::with_name("line_length")
                .short("l")
                .long("line-length")
                .takes_value(true)
                .default_value("88")
                .validator(|v| match v.parse::<u8>() {
                    Ok(_) => Ok(()),
                    Err(_) => Err(String::from(
                        "Line length must be a positive integer lower than 255",
                    )),
                }),
        )
        .arg(Arg::with_name("py36").long("py36").takes_value(false))
        .arg(Arg::with_name("pyi").long("pyi").takes_value(false))
        .arg(
            Arg::with_name("skip_string_normalization")
                .short("S")
                .long("skip-string-normalization")
                .takes_value(false),
        )
        .arg(Arg::with_name("check").long("check").takes_value(false))
        .arg(Arg::with_name("diff").long("diff").takes_value(false))
        .arg(
            Arg::with_name("fast")
                .long("fast")
                .takes_value(false)
                .conflicts_with("safe"),
        )
        .arg(
            Arg::with_name("safe")
                .long("safe")
                .takes_value(false)
                .conflicts_with("fast"),
        )
        .arg(
            Arg::with_name("include")
                .long("include")
                .takes_value(true)
                .default_value(DEFAULT_INCLUDES),
        )
        .arg(
            Arg::with_name("exclude")
                .long("exclude")
                .takes_value(true)
                .default_value(DEFAULT_EXCLUDES),
        )
        .arg(
            Arg::with_name("quite")
                .short("q")
                .long("quite")
                .takes_value(false),
        )
        .arg(
            Arg::with_name("verbose")
                .short("v")
                .long("verbose")
                .takes_value(false),
        )
        .arg(
            Arg::with_name("config")
                .long("config")
                .takes_value(true)
                .validator(path_exists),
        )
        .arg(
            Arg::with_name("src")
                .multiple(true)
                .required(true)
                .validator(|v| {
                    if Path::new(&v).exists() {
                        Ok(())
                    } else {
                        Err(format!("Path {} does not exist", v))
                    }
                }),
        );
    let matches = app.get_matches();
    let opts = Options {
        line_length: matches
            .value_of("line_length")
            .unwrap()
            .parse::<u8>()
            .unwrap(),
        check: matches.is_present("check"),
        diff: matches.is_present("diff"),
        fast: matches.is_present("fast"),
        pyi: matches.is_present("pyi"),
        py36: matches.is_present("py36"),
        skip_string_normalization: matches.is_present("skip_string_normalization"),
        quiet: matches.is_present("quiet"),
        verbose: matches.is_present("verbose"),
        include: matches.value_of("include").unwrap(),
        exclude: matches.value_of("exclude").unwrap(),
        config: matches.value_of("config"),
        src: matches.values_of("src").unwrap().into_iter().collect(),
    };
    let json = serde_json::to_string(&opts).unwrap();
    let mut stream = UnixStream::connect(matches.value_of("socket").unwrap()).unwrap();
    stream.write_all(format!("{}\n", json).as_bytes()).unwrap();
    let reader = BufReader::new(stream);
    for line in reader.lines() {
        match line {
            Ok(data) => match data.as_bytes() {
                [0, ret_code] => ::std::process::exit(*ret_code as i32),
                _ => println!("{}", data),
            },
            Err(err) => eprintln!("{}", err),
        }
    }
    //
    //
    //    let mut buf: [u8;1] = [0];
    //    stream.read_exact(&mut buf).unwrap();
    //    match buf[0] {
    //        0 => eprintln!("Fail!"),
    //        1 => println!("Success!"),
    //        _ => eprintln!("Epic Fail!"),
    //    };
}
