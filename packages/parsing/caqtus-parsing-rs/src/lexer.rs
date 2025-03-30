use logos::{Logos, Span};
use std::fmt::Display;
use std::num::{ParseFloatError, ParseIntError};

#[derive(Debug, PartialEq, Clone, Default)]
pub enum LexingError {
    ParseFloatError(ParseFloatError),
    ParseIntError(ParseIntError),
    #[default]
    InvalidToken,
}

impl From<ParseIntError> for LexingError {
    fn from(err: ParseIntError) -> Self {
        LexingError::ParseIntError(err)
    }
}

impl From<ParseFloatError> for LexingError {
    fn from(err: ParseFloatError) -> Self {
        LexingError::ParseFloatError(err)
    }
}

fn callback_integer(lex: &mut logos::Lexer<Token>) -> Result<isize, LexingError> {
    let slice = lex.slice().replace("_", "");
    slice.parse().map_err(LexingError::from)
}

fn callback_float(lex: &mut logos::Lexer<Token>) -> Result<f64, LexingError> {
    let slice = lex.slice();
    slice.parse().map_err(LexingError::from)
}

#[derive(Logos, Debug, Clone, PartialEq)]
#[logos(error = LexingError)]
#[logos(skip r" ")]
pub enum Token {
    Error(LexingError),
    #[regex(r"[\+-]?\d+", callback_integer, priority = 3)]
    Integer(isize),
    #[regex(r"[\+-]?(\d+(\.\d*)?|\.\d+)([eE][\+-]?\d+)?", callback_float)]
    Float(f64),
    #[regex(r"[_a-zA-Z\p{Greek}°][_a-zA-Z0-9\p{Greek}°]*|%", |lex| lex.slice().to_string())]
    Name(String),
    #[token(".")]
    Dot,
    #[token("+")]
    Plus,
    #[token("-")]
    Minus,
    #[token("*")]
    Multiply,
    #[token("/")]
    Divide,
    #[token("^")]
    Power,
    #[token("(")]
    LParen,
    #[token(")")]
    RParen,
    #[token(",")]
    Comma,
}

impl Display for Token {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Token::Integer(value) => write!(f, "Integer({})", value),
            Token::Float(value) => write!(f, "Float({})", value),
            Token::Name(name) => write!(f, "Name({})", name),
            Token::Dot => write!(f, "Dot"),
            Token::Plus => write!(f, "Plus"),
            Token::Minus => write!(f, "Minus"),
            Token::Multiply => write!(f, "Multiply"),
            Token::Divide => write!(f, "Divide"),
            Token::Power => write!(f, "Power"),
            Token::LParen => write!(f, "LParen"),
            Token::RParen => write!(f, "RParen"),
            Token::Comma => write!(f, "Comma"),
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
