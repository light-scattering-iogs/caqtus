use caqtus_parsing_rs::{parse, ParseNode};

#[test]
fn test_can_parse_two_factors()
{
    let result = parse("1 * 2");
    assert_eq!(
        result,
        Ok(ParseNode::Multiply(
            Box::new(ParseNode::Integer(1)),
            Box::new(ParseNode::Integer(2))
        ))
    );
}

#[test]
fn test_can_parse_three_factors()
{
    let result = parse("1 * 2 * 3");
    assert_eq!(
        result,
        Ok(ParseNode::Multiply(
            Box::new(ParseNode::Multiply(
                Box::new(ParseNode::Integer(1)),
                Box::new(ParseNode::Integer(2))
            )),
            Box::new(ParseNode::Integer(3))
        ))
    );
}

#[test]
fn test_can_parse_multiplication_and_division()
{
    let result = parse("10 MHz / s * 3");
    assert_eq!(
        result,
        Ok(ParseNode::Multiply(
            Box::new(ParseNode::Divide(
                Box::new(ParseNode::Quantity {
                    value: 10.0,
                    unit: "MHz".to_string()
                }),
                Box::new(ParseNode::Identifier("s".to_string()))
            )),
            Box::new(ParseNode::Integer(3))
        ))
    );
}

#[test]
fn test_parenthesis_priority()
{
    let result = parse("10 MHz / (s * 3)");
    assert_eq!(
        result,
        Ok(ParseNode::Divide(
            Box::new(ParseNode::Quantity {
                value: 10.0,
                unit: "MHz".to_string()
            }),
            Box::new(ParseNode::Multiply(
                Box::new(ParseNode::Identifier("s".to_string())),
                Box::new(ParseNode::Integer(3))
            ))
        ))
    );

}

#[test]
fn test_can_divide_quantities()
{
    let result = parse("10 MHz / 2 kHz");
    assert_eq!(
        result,
        Ok(ParseNode::Divide(
            Box::new(ParseNode::Quantity {
                value: 10.0,
                unit: "MHz".to_string()
            }),
            Box::new(ParseNode::Quantity {
                value: 2.0,
                unit: "kHz".to_string()
            })
        ))
    );
}

#[test]
fn test_can_multiply_unary()
{
    let result = parse("2 * -variable");
    assert_eq!(
        result,
        Ok(ParseNode::Multiply(
            Box::new(ParseNode::Integer(2)),
            Box::new(ParseNode::Negate(Box::new(ParseNode::Identifier(
                "variable".to_string()
            ))))
        ))
    );
}
