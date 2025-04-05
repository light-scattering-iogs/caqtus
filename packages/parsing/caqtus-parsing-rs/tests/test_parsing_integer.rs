use caqtus_parsing_rs::{ParseNode, parse};

#[test]
fn successfully_parse_integer_string() {
    let result = parse("45").unwrap();
    assert_eq!(
        result,
        ParseNode::Integer {
            value: 45,
            span: (0..2).into(),
        }
    );
}
#[test]
fn successfully_parse_integer_string_with_plus() {
    assert_eq!(parse("+45").unwrap().to_string(), "+(45)");
}
#[test]
fn successfully_parse_negative_integer_string() {
    assert_eq!(parse("-45").unwrap().to_string(), "-(45)");
}

#[test]
fn successfully_parse_leading_zero_integer() {
    let result = parse("01").unwrap();
    assert_eq!(
        result,
        ParseNode::Integer {
            value: 1,
            span: (0..2).into(),
        }
    );
}

#[test]
fn successfully_parse_leading_zero_with_only_zero() {
    let result = parse("0").unwrap();
    assert_eq!(
        result,
        ParseNode::Integer {
            value: 0,
            span: (0..1).into()
        }
    );
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
