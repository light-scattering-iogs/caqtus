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
    Integer {
        value: isize,
        span: SimpleSpan,
    },
    Float {
        value: f64,
        span: SimpleSpan,
    },
    Quantity {
        value: f64,
        unit: String,
        span: SimpleSpan,
    },
    Identifier {
        name: String,
        span: SimpleSpan,
    },
    UnaryOperation {
        operator: UnaryOperator,
        operand: Box<ParseNode>,
        span: SimpleSpan,
    },
    BinaryOperation {
        operator: BinaryOperator,
        lhs: Box<ParseNode>,
        rhs: Box<ParseNode>,
        span: SimpleSpan,
    },
    Call {
        name: String,
        args: Vec<ParseNode>,
        span: SimpleSpan,
    },
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
            ParseNode::Integer { value, .. } => write!(f, "{}", value),
            ParseNode::Float { value, .. } => write!(f, "{:?}", value),
            ParseNode::Quantity { value, unit, .. } => write!(f, "{:?} {}", value, unit),
            ParseNode::Identifier { name, .. } => write!(f, "{}", name),
            ParseNode::UnaryOperation {
                operator, operand, ..
            } => write!(f, "{}({})", operator, operand),
            ParseNode::BinaryOperation {
                operator, lhs, rhs, ..
            } => {
                write!(f, "({} {} {})", lhs, operator, rhs)
            }
            ParseNode::Call { name, args, .. } => {
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
        Token::Integer(value) = e => ParseNode::Integer{value, span: e.span()},
        Token::Float(value) = e => ParseNode::Float{value, span: e.span()},
    };
    let quantity = select! {
        Token::Integer(value) => value as f64,
        Token::Float(value) => value,
    }
    .then(select! {Token::Name(unit) => unit})
    .map_with(|(value, unit), e| ParseNode::Quantity {
        value,
        unit,
        span: e.span(),
    });
    quantity
        .or(number)
        .or(identifier().map_with(|name, e| ParseNode::Identifier {
            name,
            span: e.span(),
        }))
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
            .map_with(|(name, args), e| ParseNode::Call {
                name,
                args,
                span: e.span(),
            });
        let sub_expr = call
            .or(atom())
            .or(expr.delimited_by(just(Token::LParen), just(Token::RParen)));
        let arithmetic_expr = sub_expr.pratt((
            infix(right(4), just(Token::Power), |left, _, right, e| {
                ParseNode::BinaryOperation {
                    operator: BinaryOperator::Power,
                    lhs: Box::new(left),
                    rhs: Box::new(right),
                    span: e.span(),
                }
            }),
            prefix(3, just(Token::Plus), |_, operand, e| {
                ParseNode::UnaryOperation {
                    operator: UnaryOperator::Plus,
                    operand: Box::new(operand),
                    span: e.span(),
                }
            }),
            prefix(3, just(Token::Minus), |_, operand, e| {
                ParseNode::UnaryOperation {
                    operator: UnaryOperator::Negate,
                    operand: Box::new(operand),
                    span: e.span(),
                }
            }),
            infix(left(2), just(Token::Multiply), |left, _, right, e| {
                ParseNode::BinaryOperation {
                    operator: BinaryOperator::Multiply,
                    lhs: Box::new(left),
                    rhs: Box::new(right),
                    span: e.span(),
                }
            }),
            infix(left(2), just(Token::Divide), |left, _, right, e| {
                ParseNode::BinaryOperation {
                    operator: BinaryOperator::Divide,
                    lhs: Box::new(left),
                    rhs: Box::new(right),
                    span: e.span(),
                }
            }),
            infix(left(1), just(Token::Plus), |left, _, right, e| {
                ParseNode::BinaryOperation {
                    operator: BinaryOperator::Add,
                    lhs: Box::new(left),
                    rhs: Box::new(right),
                    span: e.span(),
                }
            }),
            infix(left(1), just(Token::Minus), |left, _, right, e| {
                ParseNode::BinaryOperation {
                    operator: BinaryOperator::Subtract,
                    lhs: Box::new(left),
                    rhs: Box::new(right),
                    span: e.span(),
                }
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
