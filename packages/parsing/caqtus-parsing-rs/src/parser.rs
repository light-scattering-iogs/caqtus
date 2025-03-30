use crate::lexer::{Token, lex};
use chumsky::error::Rich;
use chumsky::input::{Input, Stream, ValueInput};
use chumsky::prelude::{end, just};
use chumsky::span::SimpleSpan;
use chumsky::{Parser, extra, select};

#[derive(Debug, PartialEq)]
pub enum ParseNode {
    Integer(isize),
    Float(f64),
    Identifier(String),
}

fn parser<'a, I>() -> impl Parser<'a, I, ParseNode, extra::Err<Rich<'a, Token>>>
where
    I: ValueInput<'a, Token = Token, Span = SimpleSpan>,
{
    let number = select! {
        Token::Integer(value) => ParseNode::Integer(value),
        Token::Float(value) => ParseNode::Float(value),
    };
    let identifier = select! {
        Token::Name(name) => vec![name],
    }
    .foldl(
        just(Token::Dot)
            .ignore_then(select! {
                Token::Name(name) => name,
            })
            .repeated(),
        |mut lhs, name| {
            lhs.push(name);
            lhs
        },
    )
    .map(|names| ParseNode::Identifier(names.join(".")));
    let atom = number.or(identifier);
    atom.then_ignore(end())
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
    fn successfully_parse_leading_zero_integer() {
        let result = parse("01");
        assert_eq!(result, Ok(ParseNode::Integer(1)));
    }

    #[test]
    fn successfully_parse_leading_zero_with_only_zero() {
        let result = parse("0");
        assert_eq!(result, Ok(ParseNode::Integer(0)));
    }
    #[test]
    fn fails_to_parse_huge_integer_string() {
        let result = parse("123456789012345678901234567890");
        assert!(result.is_err());
    }

    #[test]
    fn successfully_parse_float_string() {
        let result = parse("45.0");
        assert_eq!(result, Ok(ParseNode::Float(45.0)));
    }

    #[test]
    fn successfully_parse_float_string_with_sign() {
        let result = parse("+45.0");
        assert_eq!(result, Ok(ParseNode::Float(45.0)));
        let result = parse("-45.0");
        assert_eq!(result, Ok(ParseNode::Float(-45.0)));
    }

    #[test]
    fn successfully_parse_float_string_with_exponent() {
        let result = parse("45.0e10");
        assert_eq!(result, Ok(ParseNode::Float(45.0e10)));
        let result = parse("45.0E10");
        assert_eq!(result, Ok(ParseNode::Float(45.0e10)));
    }

    #[test]
    fn successfully_parse_float_string_with_exponent_and_sign() {
        let result = parse("-45.0e+10");
        assert_eq!(result, Ok(ParseNode::Float(-45.0e10)));
        let result = parse("45.0e-10");
        assert_eq!(result, Ok(ParseNode::Float(45.0e-10)));
    }

    #[test]
    fn fails_to_parse_number_seperated_by_space() {
        let result = parse("45 0");
        assert!(result.is_err());
    }

    #[test]
    fn successfully_parse_identifier() {
        let result = parse("a");
        assert_eq!(result, Ok(ParseNode::Identifier("a".to_string())));
    }

    #[test]
    fn successfully_parse_identifier_with_dot() {
        let result = parse("a.b");
        assert_eq!(result, Ok(ParseNode::Identifier("a.b".to_string())));
    }
}
