use caqtus_parsing_rs::{parse, ParseNode};

#[test]
fn successfully_parse_addition() {
    let result = parse("1 + 2");
    assert_eq!(
        result,
        Ok(ParseNode::Add(
            Box::new(ParseNode::Integer(1)),
            Box::new(ParseNode::Integer(2))
        ))
    );
}

#[test]
fn successfully_parse_left_associative_subtraction() {
    let result = parse("1 - 2 - 3");
    assert_eq!(
        result,
        Ok(ParseNode::Subtract(
            Box::new(ParseNode::Subtract(
                Box::new(ParseNode::Integer(1)),
                Box::new(ParseNode::Integer(2))
            )),
            Box::new(ParseNode::Integer(3))
        ))
    );
}

#[test]
fn test_can_parse_unit_addition() {
    let result = parse("1 kHz + 2 MHz");
    assert_eq!(
        result,
        Ok(ParseNode::Add(
            Box::new(ParseNode::Quantity {
                value: 1.0,
                unit: "kHz".to_string()
            }),
            Box::new(ParseNode::Quantity {
                value: 2.0,
                unit: "MHz".to_string()
            })
        ))
    );
}

#[test]
fn can_add_negative_numbers() {
    let result = parse("-1 + -2");
    assert_eq!(
        result,
        Ok(ParseNode::Add(
            Box::new(ParseNode::Integer(-1)),
            Box::new(ParseNode::Integer(-2))
        ))
    );
}
