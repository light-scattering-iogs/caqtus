use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::fmt::Display;

#[pyclass(frozen, eq)]
#[derive(Debug)]
enum ParseNode {
    Integer {
        value: isize,
    },
    Float {
        value: f64,
    },
    Quantity {
        value: f64,
        unit: String,
    },
    Identifier {
        name: String,
    },
    Add {
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
    },
    Subtract {
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
    },
    Multiply {
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
    },
    Divide {
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
    },
    Negate {
        rhs: Py<ParseNode>,
    },
    Power {
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
    },
    Call {
        name: String,
        args: Vec<Py<ParseNode>>,
    },
}

impl PartialEq for ParseNode {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ParseNode::Integer { value: a }, ParseNode::Integer { value: b }) => a == b,
            (ParseNode::Float { value: a }, ParseNode::Float { value: b }) => a == b,
            (
                ParseNode::Quantity { value: a, unit: ua },
                ParseNode::Quantity { value: b, unit: ub },
            ) => a == b && ua == ub,
            (ParseNode::Identifier { name: a }, ParseNode::Identifier { name: b }) => a == b,
            (
                ParseNode::Add {
                    lhs: a_lhs,
                    rhs: a_rhs,
                },
                ParseNode::Add {
                    lhs: b_lhs,
                    rhs: b_rhs,
                },
            ) => a_lhs.get() == b_lhs.get() && a_rhs.get() == b_rhs.get(),
            (
                ParseNode::Subtract {
                    lhs: a_lhs,
                    rhs: a_rhs,
                },
                ParseNode::Subtract {
                    lhs: b_lhs,
                    rhs: b_rhs,
                },
            ) => a_lhs.get() == b_lhs.get() && a_rhs.get() == b_rhs.get(),
            (
                ParseNode::Multiply {
                    lhs: a_lhs,
                    rhs: a_rhs,
                },
                ParseNode::Multiply {
                    lhs: b_lhs,
                    rhs: b_rhs,
                },
            ) => a_lhs.get() == b_lhs.get() && a_rhs.get() == b_rhs.get(),
            (
                ParseNode::Divide {
                    lhs: a_lhs,
                    rhs: a_rhs,
                },
                ParseNode::Divide {
                    lhs: b_lhs,
                    rhs: b_rhs,
                },
            ) => a_lhs.get() == b_lhs.get() && a_rhs.get() == b_rhs.get(),
            (ParseNode::Negate { rhs: a_rhs }, ParseNode::Negate { rhs: b_rhs }) => {
                a_rhs.get() == b_rhs.get()
            }
            (
                ParseNode::Power {
                    lhs: a_lhs,
                    rhs: a_rhs,
                },
                ParseNode::Power {
                    lhs: b_lhs,
                    rhs: b_rhs,
                },
            ) => a_lhs.get() == b_lhs.get() && a_rhs.get() == b_rhs.get(),
            (
                ParseNode::Call {
                    name: a_name,
                    args: a_args,
                },
                ParseNode::Call {
                    name: b_name,
                    args: b_args,
                },
            ) => {
                a_name == b_name
                    && a_args.len() == b_args.len()
                    && a_args.iter().zip(b_args).all(|(a, b)| a.get() == b.get())
            }
            _ => false,
        }
    }
}

impl ParseNode {
    fn repr(&self) -> String {
        match self {
            ParseNode::Integer { value } => format!("Integer({})", value),
            ParseNode::Float { value } => format!("Float({})", value),
            ParseNode::Quantity { value, unit } => {
                format!("Quantity({}, {})", value, unit)
            }
            ParseNode::Identifier { name } => format!("Identifier({})", name),
            ParseNode::Add { lhs, rhs } => {
                format!("Add({}, {})", lhs.get().repr(), rhs.get().repr())
            }
            ParseNode::Subtract { lhs, rhs } => {
                format!("Subtract({}, {})", lhs.get().repr(), rhs.get().repr())
            }
            ParseNode::Multiply { lhs, rhs } => {
                format!("Multiply({}, {})", lhs.get().repr(), rhs.get().repr())
            }
            ParseNode::Divide { lhs, rhs } => {
                format!("Divide({}, {})", lhs.get().repr(), rhs.get().repr())
            }
            ParseNode::Negate { rhs } => format!("Negate({})", rhs.get().repr()),
            ParseNode::Power { lhs, rhs } => {
                format!("Power({}, {})", lhs.get().repr(), rhs.get().repr())
            }
            ParseNode::Call { name, args } => {
                let args_str = args
                    .iter()
                    .map(|arg| arg.get().repr())
                    .collect::<Vec<_>>()
                    .join(", ");
                format!("Call({}, [{}])", name, args_str)
            }
        }
    }
}

#[pymethods]
impl ParseNode {
    fn __repr__(&self) -> String {
        self.repr()
    }
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

fn convert(py: Python<'_>, ast: caqtus_parsing_rs::ParseNode) -> ParseNode {
    match ast {
        caqtus_parsing_rs::ParseNode::Integer(value) => ParseNode::Integer { value },
        caqtus_parsing_rs::ParseNode::Float(value) => ParseNode::Float { value },
        caqtus_parsing_rs::ParseNode::Quantity { value, unit } => {
            ParseNode::Quantity { value, unit }
        }
        caqtus_parsing_rs::ParseNode::Identifier(name) => ParseNode::Identifier { name },
        caqtus_parsing_rs::ParseNode::Add(lhs, rhs) => ParseNode::Add {
            lhs: Py::new(py, convert(py, *lhs)).unwrap(),
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Negate(rhs) => ParseNode::Negate {
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        _ => todo!(),
    }
}

#[pyfunction]
fn parse(py: Python<'_>, string: &str) -> Result<ParseNode, ParseError> {
    py.allow_threads(|| caqtus_parsing_rs::parse(string).map_err(|errs| errs[0].clone().into()))
        .map(|ast| convert(py, ast))
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
    use pyo3::Python;

    #[test]
    fn test_parse() {
        Python::with_gil(|py| {
            let _result = parse(py, "1 + 2");
        });
    }
}
