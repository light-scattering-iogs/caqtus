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

pub fn parse(input: &str) -> Result<ParseNode, Vec<Rich<Token>>> {
    let token_iter = lex(input).map(|(token, span)| (token, span.into()));
    let token_stream =
        Stream::from_iter(token_iter).map((0..input.len()).into(), |(t, s): (_, _)| (t, s));
    parser().parse(token_stream).into_result()
}
