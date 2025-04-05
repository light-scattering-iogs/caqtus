use caqtus_parsing_rs::parse;

#[test]
fn successfully_parse_quantity_integer_prefix() {
    assert_eq!(parse("10 MHz").unwrap().to_string(), "10.0 MHz");
}

#[test]
fn successfully_parse_quantity_float_prefix() {
    assert_eq!(parse("10.0 MHz").unwrap().to_string(), "10.0 MHz");
}

#[test]
fn successfully_parse_quantity_float_prefix_with_sign() {
    assert_eq!(parse("+10.0 MHz").unwrap().to_string(), "+(10.0 MHz)");
    assert_eq!(parse("-10.0 MHz").unwrap().to_string(), "-(10.0 MHz)");
}
