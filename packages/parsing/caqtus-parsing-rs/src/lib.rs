mod lexer;

use std::num::ParseIntError;

#[derive(Debug, PartialEq)]
pub enum AST {
    Integer(i64),
}

pub fn parse(string: &str) -> Result<AST, ParseIntError> {
    Ok(AST::Integer(string.parse::<i64>()?))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn successfully_parse_integer_string() {
        let result = parse("45");
        assert_eq!(result, Ok(AST::Integer(45)));
    }
}
