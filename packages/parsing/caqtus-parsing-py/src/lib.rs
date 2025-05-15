mod parameter_type;

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

impl From<caqtus_parsing_rs::BinaryOperator> for BinaryOperator {
    fn from(op: caqtus_parsing_rs::BinaryOperator) -> Self {
        match op {
            caqtus_parsing_rs::BinaryOperator::Add => BinaryOperator::Plus,
            caqtus_parsing_rs::BinaryOperator::Subtract => BinaryOperator::Minus,
            caqtus_parsing_rs::BinaryOperator::Multiply => BinaryOperator::Times,
            caqtus_parsing_rs::BinaryOperator::Divide => BinaryOperator::Div,
            caqtus_parsing_rs::BinaryOperator::Power => BinaryOperator::Pow,
        }
    }
}

#[pyclass(frozen, eq)]
#[derive(Debug, PartialEq, Clone)]
enum UnaryOperator {
    Neg,
    Plus,
}

impl From<caqtus_parsing_rs::UnaryOperator> for UnaryOperator {
    fn from(op: caqtus_parsing_rs::UnaryOperator) -> Self {
        match op {
            caqtus_parsing_rs::UnaryOperator::Negate => UnaryOperator::Neg,
            caqtus_parsing_rs::UnaryOperator::Plus => UnaryOperator::Plus,
        }
    }
}

#[pyclass(frozen)]
enum ParseNode {
    Integer {
        value: isize,
        span: (usize, usize),
    },
    Float {
        value: f64,
        span: (usize, usize),
    },
    Quantity {
        value: f64,
        unit: String,
        span: (usize, usize),
    },
    Identifier {
        name: String,
        span: (usize, usize),
    },
    UnaryOperation {
        operator: UnaryOperator,
        operand: Py<ParseNode>,
        span: (usize, usize),
    },
    BinaryOperation {
        operator: BinaryOperator,
        lhs: Py<ParseNode>,
        rhs: Py<ParseNode>,
        span: (usize, usize),
    },
    Call {
        name: String,
        args: Py<PyTuple>,
        span: (usize, usize),
    },
}

impl ParseNode {
    fn equal(&self, py: Python<'_>, other: &ParseNode) -> PyResult<bool> {
        match (self, other) {
            (ParseNode::Integer { value: a, .. }, ParseNode::Integer { value: b, .. }) => {
                Ok(a == b)
            }
            (ParseNode::Float { value: a, .. }, ParseNode::Float { value: b, .. }) => Ok(a == b),
            (
                ParseNode::Quantity {
                    value: a, unit: ua, ..
                },
                ParseNode::Quantity {
                    value: b, unit: ub, ..
                },
            ) => Ok(a == b && ua == ub),
            (ParseNode::Identifier { name: a, .. }, ParseNode::Identifier { name: b, .. }) => {
                Ok(a == b)
            }
            (
                ParseNode::BinaryOperation {
                    operator: op_a,
                    lhs: lhs_a,
                    rhs: rhs_a,
                    ..
                },
                ParseNode::BinaryOperation {
                    operator: op_b,
                    lhs: lhs_b,
                    rhs: rhs_b,
                    ..
                },
            ) => Ok(op_a == op_b
                && lhs_a.bind(py).as_any().eq(lhs_b.bind(py))?
                && rhs_a.bind(py).as_any().eq(rhs_b.bind(py))?),
            (
                ParseNode::UnaryOperation {
                    operator: op_a,
                    operand: rhs_a,
                    ..
                },
                ParseNode::UnaryOperation {
                    operator: op_b,
                    operand: rhs_b,
                    ..
                },
            ) => Ok(op_a == op_b && rhs_a.bind(py).as_any().eq(rhs_b.bind(py))?),
            (
                ParseNode::Call {
                    name: a_name,
                    args: a_args,
                    ..
                },
                ParseNode::Call {
                    name: b_name,
                    args: b_args,
                    ..
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
            ParseNode::Integer { value, .. } => format!("Integer({})", value),
            ParseNode::Float { value, .. } => format!("Float({})", value),
            ParseNode::Quantity { value, unit, .. } => {
                format!("Quantity({}, \"{}\")", value, unit)
            }
            ParseNode::Identifier { name, .. } => format!("Identifier(\"{}\")", name),
            ParseNode::UnaryOperation {
                operator, operand, ..
            } => {
                format!(
                    "UnaryOperation({:?}, {})",
                    operator,
                    operand.bind(py).as_any().repr().unwrap()
                )
            }
            ParseNode::BinaryOperation {
                operator, lhs, rhs, ..
            } => {
                format!(
                    "BinaryOperation({:?}, {}, {})",
                    operator,
                    lhs.bind(py).as_any().repr().unwrap(),
                    rhs.bind(py).as_any().repr().unwrap()
                )
            }
            ParseNode::Call { name, args, .. } => {
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
        caqtus_parsing_rs::ParseNode::Integer { value, span } => ParseNode::Integer {
            value,
            span: (span.start, span.end),
        },
        caqtus_parsing_rs::ParseNode::Float { value, span } => ParseNode::Float {
            value,
            span: (span.start, span.end),
        },
        caqtus_parsing_rs::ParseNode::Quantity { value, unit, span } => ParseNode::Quantity {
            value,
            unit,
            span: (span.start, span.end),
        },
        caqtus_parsing_rs::ParseNode::Identifier { name, span } => ParseNode::Identifier {
            name,
            span: (span.start, span.end),
        },
        caqtus_parsing_rs::ParseNode::BinaryOperation {
            operator,
            lhs,
            rhs,
            span,
        } => ParseNode::BinaryOperation {
            operator: operator.into(),
            lhs: convert(py, *lhs).into_pyobject(py).unwrap().unbind(),
            rhs: convert(py, *rhs).into_pyobject(py).unwrap().unbind(),
            span: (span.start, span.end),
        },
        caqtus_parsing_rs::ParseNode::UnaryOperation {
            operator,
            operand,
            span,
        } => ParseNode::UnaryOperation {
            operator: operator.into(),
            operand: convert(py, *operand).into_pyobject(py).unwrap().unbind(),
            span: (span.start, span.end),
        },
        caqtus_parsing_rs::ParseNode::Call { name, args, span } => ParseNode::Call {
            name,
            args: PyTuple::new(
                py,
                args.into_iter()
                    .map(|arg| convert(py, arg).into_pyobject(py).unwrap())
                    .collect::<Vec<_>>(),
            )
            .unwrap()
            .unbind(),
            span: (span.start, span.end),
        },
    }
}

#[pyfunction]
fn parse(py: Python<'_>, string: &str) -> Result<ParseNode, ParseError> {
    py.allow_threads(|| caqtus_parsing_rs::parse(string).map_err(|errs| errs[0].clone().into()))
        .map(|ast| convert(py, ast))
}

#[pyfunction]
fn compile(py: Python<'_>, string: &str, parameter_types: )

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse, m)?)?;
    m.add_class::<ParseNode>()?;
    m.add_class::<ParseError>()?;
    m.add_class::<BinaryOperator>()?;
    m.add_class::<UnaryOperator>()?;
    m.add_class::<parameter_type::ParameterType>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_parse() {}
}
