use caqtus_parsing_rs::parse;

#[test]
fn successfully_parse_identifier() {
    assert_eq!(parse("a").unwrap().to_string(), "a");
}

#[test]
fn successfully_parse_greek_characters() {
    assert_eq!(parse("αβγ").unwrap().to_string(), "αβγ");
}

#[test]
fn successfully_parse_degree_sign() {
    assert_eq!(parse("°C").unwrap().to_string(), "°C");
}

#[test]
fn successfully_parse_percent() {
    assert_eq!(parse("%").unwrap().to_string(), "%");
}

#[test]
fn fails_to_parse_identifier_with_percent() {
    let result = parse("a%");
    assert!(result.is_err());
}
#[test]
fn successfully_parse_identifier_with_single_dot() {
    assert_eq!(parse("a.b").unwrap().to_string(), "a.b");
}

#[test]
fn successfully_parse_identifier_with_multiple_dots() {
    assert_eq!(parse("a.b.c").unwrap().to_string(), "a.b.c");
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
