use caqtus_parsing_rs::{parse, ParseNode};

#[test]
fn successfully_parse_identifier() {
    let result = parse("a");
    assert_eq!(result, Ok(ParseNode::Identifier("a".to_string())));
}

#[test]
fn successfully_parse_greek_characters() {
    let result = parse("αβγ");
    assert_eq!(result, Ok(ParseNode::Identifier("αβγ".to_string())));
}

#[test]
fn successfully_parse_degree_sign() {
    let result = parse("°C");
    assert_eq!(result, Ok(ParseNode::Identifier("°C".to_string())));
}

#[test]
fn successfully_parse_percent() {
    let result = parse("%");
    assert_eq!(result, Ok(ParseNode::Identifier("%".to_string())));
}

#[test]
fn fails_to_parse_identifier_with_percent() {
    let result = parse("a%");
    assert!(result.is_err());
}
#[test]
fn successfully_parse_identifier_with_single_dot() {
    let result = parse("a.b");
    assert_eq!(result, Ok(ParseNode::Identifier("a.b".to_string())));
}

#[test]
fn successfully_parse_identifier_with_multiple_dots() {
    let result = parse("a.b.c");
    assert_eq!(result, Ok(ParseNode::Identifier("a.b.c".to_string())));
}

#[test]
fn fails_to_parse_identifier_with_trailing_dot() {
    let result = parse("a.");
    assert!(result.is_err());
}

#[test]
fn fails_to_parse_identifier_with_leading_dot() {
    let result = parse(".a");
    assert!(result.is_err());
}

#[test]
fn fails_to_parse_identifier_with_consecutive_dots() {
    let result = parse("a..b");
    assert!(result.is_err());
}