use pyo3::prelude::*;
use std::num::ParseIntError;

#[allow(clippy::upper_case_acronyms)]
#[pyclass(frozen, eq)]
#[derive(PartialEq, Debug)]
enum AST {
    Integer { value: i64 },
}

impl From<caqtus_parsing_rs::AST> for AST {
    fn from(ast: caqtus_parsing_rs::AST) -> Self {
        match ast {
            caqtus_parsing_rs::AST::Integer(value) => AST::Integer { value },
        }
    }
}

#[pyfunction]
fn parse(string: &str) -> Result<AST, ParseIntError> {
    caqtus_parsing_rs::parse(string).map(AST::from)
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_class::<AST>()?;
    Ok(())
}

#[cfg(test)]
mod tests {}
