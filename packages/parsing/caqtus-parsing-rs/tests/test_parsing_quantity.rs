use caqtus_parsing_rs::{ParseNode, parse};

#[test]
fn successfully_parse_quantity_integer_prefix() {
    let result = parse("10 MHz");
    assert_eq!(
        result,
        Ok(ParseNode::Quantity {
            value: 10.0,
            unit: "MHz".to_string()
        })
    );
}

#[test]
fn successfully_parse_quantity_float_prefix() {
    let result = parse("10.0 MHz");
    assert_eq!(
        result,
        Ok(ParseNode::Quantity {
            value: 10.0,
            unit: "MHz".to_string()
        })
    );
}

#[test]
fn successfully_parse_quantity_float_prefix_with_sign() {
    let result = parse("+10.0 MHz");
    assert_eq!(
        result,
        Ok(ParseNode::Quantity {
            value: 10.0,
            unit: "MHz".to_string()
        })
    );
    let result = parse("-10.0 MHz");
    assert_eq!(
        result,
        Ok(ParseNode::Quantity {
            value: -10.0,
            unit: "MHz".to_string()
        })
    );
}
