use caqtus_parsing_rs::{parse, ParseNode};

#[test]
fn successfully_parse_float_string() {
    let result = parse("45.0");
    assert_eq!(result, Ok(ParseNode::Float(45.0)));
}

#[test]
fn successfully_parse_float_string_with_sign() {
    assert_eq!(parse("+45.0").unwrap().to_string(), "+(45.0)");
    assert_eq!(parse("-45.0").unwrap().to_string(), "-(45.0)");
}

#[test]
fn successfully_parse_float_string_with_exponent() {
    let result = parse("45.0e10");
    assert_eq!(result, Ok(ParseNode::Float(45.0e10)));
    let result = parse("45.0E10");
    assert_eq!(result, Ok(ParseNode::Float(45.0e10)));
}

#[test]
fn successfully_parse_float_string_with_exponent_and_sign() {
    let result = parse("45.0e+10");
    assert_eq!(result, Ok(ParseNode::Float(45.0e10)));
    let result = parse("45.0e-10");
    assert_eq!(result, Ok(ParseNode::Float(45.0e-10)));
}