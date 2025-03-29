use pyo3::prelude::*;
use std::num::ParseIntError;

#[allow(clippy::upper_case_acronyms)]
#[pyclass(frozen, eq)]
#[derive(PartialEq, Debug)]
enum ParseNode {
    Integer { value: i64 },
}

impl From<caqtus_parsing_rs::ParseNode> for ParseNode {
    fn from(ast: caqtus_parsing_rs::ParseNode) -> Self {
        match ast {
            caqtus_parsing_rs::ParseNode::Integer(value) => ParseNode::Integer { value },
        }
    }
}

#[pyfunction]
fn parse(string: &str) -> Result<ParseNode, ParseIntError> {
    caqtus_parsing_rs::parse(string).map(ParseNode::from)
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_class::<ParseNode>()?;
    Ok(())
}

#[cfg(test)]
mod tests {}
