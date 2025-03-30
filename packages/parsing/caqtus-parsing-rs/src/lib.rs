mod lexer;
mod parser;

use std::num::ParseIntError;

#[derive(Debug, PartialEq)]
pub enum ParseNode {
    Integer(i64),
}

pub fn parse(string: &str) -> Result<ParseNode, ParseIntError> {
    Ok(ParseNode::Integer(string.parse::<i64>()?))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn successfully_parse_integer_string() {
        let result = parse("45");
        assert_eq!(result, Ok(ParseNode::Integer(45)));
    }
}
