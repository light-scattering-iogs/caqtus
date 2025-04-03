use caqtus_parsing_rs::parse;

#[test]
fn test_can_parse_two_factors() {
    assert_eq!(parse("1 * 2").unwrap().to_string(), "(1 * 2)");
}

#[test]
fn test_can_parse_three_factors() {
    assert_eq!(parse("1 * 2 * 3").unwrap().to_string(), "((1 * 2) * 3)");
}

#[test]
fn test_can_parse_multiplication_and_division() {
    assert_eq!(
        parse("10 MHz / s * 3").unwrap().to_string(),
        "((10 MHz / s) * 3)"
    );
}

#[test]
fn test_parenthesis_priority() {
    assert_eq!(
        parse("10 MHz / (s * 3)").unwrap().to_string(),
        "(10 MHz / (s * 3))"
    );
}

#[test]
fn test_can_divide_quantities() {
    assert_eq!(
        parse("10 MHz / 2 kHz").unwrap().to_string(),
        "(10 MHz / 2 kHz)"
    );
}

#[test]
fn test_can_multiply_unary() {
    assert_eq!(
        parse("2 * -variable").unwrap().to_string(),
        "(2 * -(variable))"
    );
}
