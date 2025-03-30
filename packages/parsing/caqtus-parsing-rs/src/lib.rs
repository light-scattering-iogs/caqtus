mod lexer;
mod parser;

pub use crate::parser::{parse, ParseNode};

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn successfully_parse_integer_string() {
        let result = parse("45");
        assert_eq!(result, Ok(ParseNode::Integer(45)));
    }
}
