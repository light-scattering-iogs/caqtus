use crate::lexer::{Token, lex};
use chumsky::error::Rich;
use chumsky::input::{Input, Stream, ValueInput};
use chumsky::span::SimpleSpan;
use chumsky::{Parser, extra, select};

#[derive(Debug, PartialEq)]
pub enum ParseNode {
    Integer(isize),
}

fn parser<'a, I>() -> impl Parser<'a, I, ParseNode, extra::Err<Rich<'a, Token>>>
where
    I: ValueInput<'a, Token = Token, Span = SimpleSpan>,
{
    let number = select! {
        Token::Integer(value) => ParseNode::Integer(value),
    };
    number
}

fn parse(input: &str) -> Result<ParseNode, Vec<Rich<Token>>> {
    let token_iter = lex(input).map(|(token, span)| (token, span.into()));
    let token_stream =
        Stream::from_iter(token_iter).map((0..input.len()).into(), |(t, s): (_, _)| (t, s));
    parser().parse(token_stream).into_result()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn successfully_parse_integer_string() {
        let result = parse("45");
        assert_eq!(result, Ok(ParseNode::Integer(45)));
    }
    #[test]
    fn successfully_parse_integer_string_with_plus() {
        let result = parse("+45");
        assert_eq!(result, Ok(ParseNode::Integer(45)));
    }
    #[test]
    fn successfully_parse_negative_integer_string() {
        let result = parse("-45");
        assert_eq!(result, Ok(ParseNode::Integer(-45)));
    }
    #[test]
    fn safely_fails_to_parse_huge_integer_string() {
        let result = parse("123456789012345678901234567890");
        assert!(result.is_err());
    }

}
