use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use std::fmt::Display;
#[pyclass(frozen, eq)]
#[derive(Debug, PartialEq, Clone)]
enum BinaryOperator {
    Plus,
    Minus,
    Times,
    Div,
    Pow,
}

#[pyclass(frozen, eq)]
#[derive(Debug, PartialEq, Clone)]
enum UnaryOperator {
    Neg,
}

#[pyclass(frozen)]
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
    UnaryOperation {
        operator: UnaryOperator,
        operand: Py<ParseNode>,
    },
    BinaryOperation {
        operator: BinaryOperator,
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
    },
    Call {
        name: String,
        args: Py<PyTuple>,
    },
}

impl ParseNode {
    fn equal(&self, py: Python<'_>, other: &ParseNode) -> PyResult<bool> {
        match (self, other) {
            (ParseNode::Integer { value: a }, ParseNode::Integer { value: b }) => Ok(a == b),
            (ParseNode::Float { value: a }, ParseNode::Float { value: b }) => Ok(a == b),
            (
                ParseNode::Quantity { value: a, unit: ua },
                ParseNode::Quantity { value: b, unit: ub },
            ) => Ok(a == b && ua == ub),
            (ParseNode::Identifier { name: a }, ParseNode::Identifier { name: b }) => Ok(a == b),
            (
                ParseNode::BinaryOperation {
                    operator: op_a,
                    lhs: lhs_a,
                    rhs: rhs_a,
                },
                ParseNode::BinaryOperation {
                    operator: op_b,
                    lhs: lhs_b,
                    rhs: rhs_b,
                },
            ) => Ok(op_a == op_b
                && lhs_a.bind(py).as_any().eq(lhs_b.bind(py))?
                && rhs_a.bind(py).as_any().eq(rhs_b.bind(py))?),
            (
                ParseNode::UnaryOperation {
                    operator: op_a,
                    operand: rhs_a,
                },
                ParseNode::UnaryOperation {
                    operator: op_b,
                    operand: rhs_b,
                },
            ) => Ok(op_a == op_b && rhs_a.bind(py).as_any().eq(rhs_b.bind(py))?),
            (
                ParseNode::Call {
                    name: a_name,
                    args: a_args,
                },
                ParseNode::Call {
                    name: b_name,
                    args: b_args,
                },
            ) => Ok(a_args.bind(py).eq(b_args.bind(py))? && a_name == b_name),
            _ => Ok(false),
        }
    }
}

#[pymethods]
impl ParseNode {
    fn __repr__(&self, py: Python<'_>) -> String {
        match self {
            ParseNode::Integer { value } => format!("Integer({})", value),
            ParseNode::Float { value } => format!("Float({})", value),
            ParseNode::Quantity { value, unit } => {
                format!("Quantity({}, \"{}\")", value, unit)
            }
            ParseNode::Identifier { name } => format!("Identifier(\"{}\")", name),
            ParseNode::UnaryOperation { operator, operand } => {
                format!(
                    "UnaryOperation({:?}, {})",
                    operator,
                    operand.bind(py).as_any().repr().unwrap()
                )
            }
            ParseNode::BinaryOperation { operator, lhs, rhs } => {
                format!(
                    "BinaryOperation({:?}, {}, {})",
                    operator,
                    lhs.bind(py).as_any().repr().unwrap(),
                    rhs.bind(py).as_any().repr().unwrap()
                )
            }
            ParseNode::Call { name, args } => {
                let args_str = args.bind(py).repr().unwrap().to_string();
                format!("Call(\"{}\", [{}])", name, args_str)
            }
        }
    }

    fn __eq__<'py>(&self, py: Python<'_>, other: Py<PyAny>) -> bool {
        if let Ok(other) = other.bind(py).downcast::<ParseNode>() {
            let other = other.get();
            self.equal(py, other).unwrap()
        } else {
            false
        }
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
    // TODO: replace all the .into_pyobject(py).unwrap().unbind() Py::new once
    //  https://github.com/PyO3/pyo3/issues/3747 is resolved
    match ast {
        caqtus_parsing_rs::ParseNode::Integer(value) => ParseNode::Integer { value },
        caqtus_parsing_rs::ParseNode::Float(value) => ParseNode::Float { value },
        caqtus_parsing_rs::ParseNode::Quantity { value, unit } => {
            ParseNode::Quantity { value, unit }
        }
        caqtus_parsing_rs::ParseNode::Identifier(name) => ParseNode::Identifier { name },
        caqtus_parsing_rs::ParseNode::Add(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Plus,
            lhs: convert(py, *lhs).into_pyobject(py).unwrap().unbind(),
            rhs: convert(py, *rhs).into_pyobject(py).unwrap().unbind(),
        },
        caqtus_parsing_rs::ParseNode::Subtract(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Minus,
            lhs: convert(py, *lhs).into_pyobject(py).unwrap().unbind(),
            rhs: convert(py, *rhs).into_pyobject(py).unwrap().unbind(),
        },
        caqtus_parsing_rs::ParseNode::Multiply(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Times,
            lhs: convert(py, *lhs).into_pyobject(py).unwrap().unbind(),
            rhs: convert(py, *rhs).into_pyobject(py).unwrap().unbind(),
        },
        caqtus_parsing_rs::ParseNode::Divide(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Div,
            lhs: convert(py, *lhs).into_pyobject(py).unwrap().unbind(),
            rhs: convert(py, *rhs).into_pyobject(py).unwrap().unbind(),
        },
        caqtus_parsing_rs::ParseNode::Power(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Pow,
            lhs: convert(py, *lhs).into_pyobject(py).unwrap().unbind(),
            rhs: convert(py, *rhs).into_pyobject(py).unwrap().unbind(),
        },
        caqtus_parsing_rs::ParseNode::Negate(operant) => ParseNode::UnaryOperation {
            operator: UnaryOperator::Neg,
            operand: convert(py, *operant).into_pyobject(py).unwrap().unbind(),
        },
        caqtus_parsing_rs::ParseNode::Call(name, args) => ParseNode::Call {
            name,
            args: PyTuple::new(
                py,
                args.into_iter()
                    .map(|arg| convert(py, arg).into_pyobject(py).unwrap())
                    .collect::<Vec<_>>(),
            )
            .unwrap()
            .unbind(),
        },
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
    m.add_class::<ParseError>()?;
    m.add_class::<BinaryOperator>()?;
    m.add_class::<UnaryOperator>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_parse() {}
}
