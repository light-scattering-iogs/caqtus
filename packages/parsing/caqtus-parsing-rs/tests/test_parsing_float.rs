use caqtus_parsing_rs::{ParseNode, parse};

#[test]
fn successfully_parse_float_string() {
    let result = parse("45.0").unwrap();
    assert_eq!(
        result,
        ParseNode::Float {
            value: 45.0,
            span: (0..4).into()
        }
    );
}

#[test]
fn successfully_parse_float_string_with_sign() {
    assert_eq!(parse("+45.0").unwrap().to_string(), "+(45.0)");
    assert_eq!(parse("-45.0").unwrap().to_string(), "-(45.0)");
}

#[test]
fn successfully_parse_float_string_with_exponent() {
    let result = parse("45.0e10").unwrap();
    assert_eq!(
        result,
        ParseNode::Float {
            value: 45.0e10,
            span: (0..7).into()
        }
    );
    let result = parse("45.0E10").unwrap();
    assert_eq!(result, ParseNode::Float{
        value: 45.0e10,
        span: (0..7).into()
    });
}

#[test]
fn successfully_parse_float_string_with_exponent_and_sign() {
    let result = parse("45.0e+10").unwrap();
    assert_eq!(
        result,
        ParseNode::Float {
            value: 45.0e10,
            span: (0..8).into()
        }
    );
    let result = parse("45.0e-10").unwrap();
    assert_eq!(result, ParseNode::Float{
        value: 45.0e-10,
        span: (0..8).into()
    });
}
