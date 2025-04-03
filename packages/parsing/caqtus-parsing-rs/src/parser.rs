use crate::lexer::{Token, lex};
use chumsky::error::Rich;
use chumsky::input::{Input, Stream, ValueInput};
use chumsky::pratt::{infix, left, prefix, right};
use chumsky::prelude::*;
use chumsky::prelude::{end, just, recursive};
use chumsky::span::SimpleSpan;
use chumsky::{Parser, extra, select};
use std::fmt::Display;

#[derive(Debug, PartialEq)]
pub enum ParseNode {
    Integer(isize),
    Float(f64),
    Quantity { value: f64, unit: String },
    Identifier(String),
    UnaryOperation(UnaryOperator, Box<ParseNode>),
    BinaryOperation(BinaryOperator, Box<ParseNode>, Box<ParseNode>),
    Call(String, Vec<ParseNode>),
}

#[derive(Debug, PartialEq)]
pub enum BinaryOperator {
    Add,
    Subtract,
    Multiply,
    Divide,
    Power,
}

#[derive(Debug, PartialEq)]
pub enum UnaryOperator {
    Negate,
    Plus,
}

impl Display for BinaryOperator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BinaryOperator::Add => write!(f, "+"),
            BinaryOperator::Subtract => write!(f, "-"),
            BinaryOperator::Multiply => write!(f, "*"),
            BinaryOperator::Divide => write!(f, "/"),
            BinaryOperator::Power => write!(f, "^"),
        }
    }
}

impl Display for UnaryOperator {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            UnaryOperator::Plus => write!(f, "+"),
            UnaryOperator::Negate => write!(f, "-"),
        }
    }
}

impl Display for ParseNode {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ParseNode::Integer(i) => write!(f, "{}", i),
            ParseNode::Float(fl) => write!(f, "{:?}", fl),
            ParseNode::Quantity { value, unit } => write!(f, "{:?} {}", value, unit),
            ParseNode::Identifier(name) => write!(f, "{}", name),
            ParseNode::UnaryOperation(operator, operand) => write!(f, "{}({})", operator, operand),
            ParseNode::BinaryOperation(operator, left, right) => {
                write!(f, "({} {} {})", left, operator, right)
            }
            ParseNode::Call(name, args) => {
                let args_str = args
                    .iter()
                    .map(|arg| arg.to_string())
                    .collect::<Vec<_>>()
                    .join(", ");
                write!(f, "{}({})", name, args_str)
            }
        }
    }
}

fn identifier<'a, I>() -> impl Parser<'a, I, String, extra::Err<Rich<'a, Token>>> + Clone
where
    I: ValueInput<'a, Token = Token, Span = SimpleSpan>,
{
    select! {
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
    .map(|names| names.join("."))
}

fn atom<'a, I>() -> impl Parser<'a, I, ParseNode, extra::Err<Rich<'a, Token>>> + Clone
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
    quantity
        .or(number)
        .or(identifier().map(ParseNode::Identifier))
}

fn parser<'a, I>() -> impl Parser<'a, I, ParseNode, extra::Err<Rich<'a, Token>>>
where
    I: ValueInput<'a, Token = Token, Span = SimpleSpan>,
{
    recursive(|expr| {
        let call = identifier()
            .then(
                expr.clone()
                    .separated_by(just(Token::Comma))
                    .allow_trailing()
                    .collect::<Vec<_>>()
                    .delimited_by(just(Token::LParen), just(Token::RParen)),
            )
            .map(|(name, args)| ParseNode::Call(name, args));
        let sub_expr = call
            .or(atom())
            .or(expr.delimited_by(just(Token::LParen), just(Token::RParen)));
        let arithmetic_expr = sub_expr.pratt((
            infix(right(4), just(Token::Power), |left, _, right, _| {
                ParseNode::BinaryOperation(BinaryOperator::Power, Box::new(left), Box::new(right))
            }),
            prefix(3, just(Token::Plus), |_, right, _| {
                ParseNode::UnaryOperation(UnaryOperator::Plus, Box::new(right))
            }),
            prefix(3, just(Token::Minus), |_, right, _| {
                ParseNode::UnaryOperation(UnaryOperator::Negate, Box::new(right))
            }),
            infix(left(2), just(Token::Multiply), |left, _, right, _| {
                ParseNode::BinaryOperation(
                    BinaryOperator::Multiply,
                    Box::new(left),
                    Box::new(right),
                )
            }),
            infix(left(2), just(Token::Divide), |left, _, right, _| {
                ParseNode::BinaryOperation(BinaryOperator::Divide, Box::new(left), Box::new(right))
            }),
            infix(left(1), just(Token::Plus), |left, _, right, _| {
                ParseNode::BinaryOperation(BinaryOperator::Add, Box::new(left), Box::new(right))
            }),
            infix(left(1), just(Token::Minus), |left, _, right, _| {
                ParseNode::BinaryOperation(
                    BinaryOperator::Subtract,
                    Box::new(left),
                    Box::new(right),
                )
            }),
        ));
        arithmetic_expr
    })
    .then_ignore(end())
}

pub fn parse(input: &str) -> Result<ParseNode, Vec<Rich<Token>>> {
    let token_iter = lex(input).map(|(token, span)| (token, span.into()));
    let token_stream =
        Stream::from_iter(token_iter).map((0..input.len()).into(), |(t, s): (_, _)| (t, s));
    parser().parse(token_stream).into_result()
}
