use pyo3::prelude::*;
use std::fmt::Display;
use pyo3::exceptions::PyValueError;

#[pyclass(frozen, eq)]
#[derive(PartialEq, Debug)]
enum ParseNode {
    Integer { value: isize },
    Float { value: f64 },
    Identifier { name: String },
}

#[pyclass(frozen)]
#[derive(Debug)]
struct ParseError {
    message: String,
}

impl<T: Display> From<T> for ParseError {
    fn from(err: T) -> Self {
        ParseError {
            message: err.to_string(),
        }
    }
}

impl From<ParseError> for PyErr {
    fn from(err: ParseError) -> Self {
        PyValueError::new_err(err.message)
    }
}

impl From<caqtus_parsing_rs::ParseNode> for ParseNode {
    fn from(ast: caqtus_parsing_rs::ParseNode) -> Self {
        match ast {
            caqtus_parsing_rs::ParseNode::Integer(value) => ParseNode::Integer { value },
            caqtus_parsing_rs::ParseNode::Float(value) => ParseNode::Float { value },
            caqtus_parsing_rs::ParseNode::Identifier(name) => ParseNode::Identifier { name },
        }
    }
}

#[pyfunction]
fn parse(string: &str) -> Result<ParseNode, ParseError> {
    caqtus_parsing_rs::parse(string)
        .map(ParseNode::from)
        .map_err(|errs| errs[0].clone().into())
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_class::<ParseNode>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn successfully_parse_integer_string() {
        let result = parse("45").unwrap();
        assert_eq!(result, ParseNode::Integer { value: 45 });
    }
}
