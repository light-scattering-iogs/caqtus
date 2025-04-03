use caqtus_parsing_rs::parse;

#[test]
fn successfully_parse_addition() {
    assert_eq!(parse("1 + 2").unwrap().to_string(), "(1 + 2)");
}

#[test]
fn successfully_parse_left_associative_subtraction() {
    assert_eq!(parse("1 - 2 - 3").unwrap().to_string(), "((1 - 2) - 3)");
}

#[test]
fn test_parentheses_priority() {
    assert_eq!(parse("1 - (2 - 3)").unwrap().to_string(), "(1 - (2 - 3))");
}

#[test]
fn can_add_number_without_spaces() {
    assert_eq!(parse("1+2").unwrap().to_string(), "(1 + 2)");
}

#[test]
fn test_can_parse_unit_addition() {
    assert_eq!(
        parse("1 kHz + 2 MHz").unwrap().to_string(),
        "(1 kHz + 2 MHz)"
    );
}

#[test]
fn can_add_negative_numbers() {
    assert_eq!(parse("-1 + -2").unwrap().to_string(), "(-1 + -2)");
}
