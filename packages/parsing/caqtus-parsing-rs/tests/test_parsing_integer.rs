use caqtus_parsing_rs::{parse, ParseNode};

#[test]
fn successfully_parse_integer_string() {
    let result = parse("45");
    assert_eq!(result, Ok(ParseNode::Integer(45)));
}
#[test]
fn successfully_parse_integer_string_with_plus() {
    let result = parse("+45");
    assert_eq!(result, Ok(ParseNode::Integer(45)));
}
#[test]
fn successfully_parse_negative_integer_string() {
    let result = parse("-45");
    assert_eq!(result, Ok(ParseNode::Integer(-45)));
}

#[test]
fn successfully_parse_leading_zero_integer() {
    let result = parse("01");
    assert_eq!(result, Ok(ParseNode::Integer(1)));
}

#[test]
fn successfully_parse_leading_zero_with_only_zero() {
    let result = parse("0");
    assert_eq!(result, Ok(ParseNode::Integer(0)));
}
#[test]
fn fails_to_parse_huge_integer_string() {
    let result = parse("123456789012345678901234567890");
    assert!(result.is_err());
}

#[test]
fn fails_to_parse_number_seperated_by_space() {
    let result = parse("45 0");
    assert!(result.is_err());
}