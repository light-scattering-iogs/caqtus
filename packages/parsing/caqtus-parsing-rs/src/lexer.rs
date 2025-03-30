use logos::{Logos, Span};
use std::fmt::Display;
use std::num::ParseIntError;

#[derive(Debug, PartialEq, Clone, Default)]
pub enum LexingError {
    ParseIntError(ParseIntError),
    #[default]
    InvalidToken,
}

impl From<ParseIntError> for LexingError {
    fn from(err: ParseIntError) -> Self {
        LexingError::ParseIntError(err)
    }
}

#[derive(Logos, Debug, Clone, PartialEq)]
#[logos(error = LexingError)]
#[logos(skip r" ")]
pub enum Token {
    Error(LexingError),
    #[regex(r"[\+|-]?[0-9]+", |lex| lex.slice().parse())]
    Integer(isize),
}

impl Display for Token {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Token::Integer(value) => write!(f, "Integer({})", value),
            Token::Error(err) => write!(f, "Error({:?})", err),
        }
    }
}

pub fn lex(input: &str) -> impl Iterator<Item = (Token, Span)> {
    Token::lexer(input).spanned().map(|(tok, span)| match tok {
        Ok(token) => (token, span),
        Err(err) => (Token::Error(err), span),
    })
}
