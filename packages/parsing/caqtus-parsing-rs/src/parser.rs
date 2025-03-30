use crate::lexer::{Token, lex};
use chumsky::error::Rich;
use chumsky::input::{Input, Stream, ValueInput};
use chumsky::pratt::{infix, left};
use chumsky::prelude::{end, just};
use chumsky::span::SimpleSpan;
use chumsky::{Parser, extra, select};

#[derive(Debug, PartialEq)]
pub enum ParseNode {
    Integer(isize),
    Float(f64),
    Quantity { value: f64, unit: String },
    Identifier(String),
    Add(Box<ParseNode>, Box<ParseNode>),
    Subtract(Box<ParseNode>, Box<ParseNode>),
}

fn parser<'a, I>() -> impl Parser<'a, I, ParseNode, extra::Err<Rich<'a, Token>>>
where
    I: ValueInput<'a, Token = Token, Span = SimpleSpan>,
{
    let number = select! {
        Token::Integer(value) => ParseNode::Integer(value),
        Token::Float(value) => ParseNode::Float(value),
    };
    let quantity = select! {
        Token::Integer(value) => value as f64,
        Token::Float(value) => value,
    }
    .then(select! {Token::Name(unit) => unit})
    .map(|(value, unit)| ParseNode::Quantity { value, unit });
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
    let atom = quantity.or(number).or(identifier);
    let expr = atom.pratt((
        infix(left(1), just(Token::Plus), |left, _, right, _| {
            ParseNode::Add(Box::new(left), Box::new(right))
        }),
        infix(left(1), just(Token::Minus), |left, _, right, _| {
            ParseNode::Subtract(Box::new(left), Box::new(right))
        }),
    ));
    expr.then_ignore(end())
}

pub fn parse(input: &str) -> Result<ParseNode, Vec<Rich<Token>>> {
    let token_iter = lex(input).map(|(token, span)| (token, span.into()));
    let token_stream =
        Stream::from_iter(token_iter).map((0..input.len()).into(), |(t, s): (_, _)| (t, s));
    parser().parse(token_stream).into_result()
}
