use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
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
    UnaryOperation(UnaryOperator, Py<ParseNode>),
    BinaryOperation(BinaryOperator, Py<ParseNode>, Py<ParseNode>),
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
                ParseNode::BinaryOperation(op_a, lhs_a, rhs_a),
                ParseNode::BinaryOperation(op_b, lhs_b, rhs_b),
            ) => op_a == op_b && lhs_a.get() == lhs_b.get() && rhs_a.get() == rhs_b.get(),
            (
                ParseNode::UnaryOperation(op_a, rhs_a),
                ParseNode::UnaryOperation(op_b, rhs_b),
            ) => op_a == op_b && rhs_a.get() == rhs_b.get(),
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
            ParseNode::UnaryOperation(op, rhs) => {
                format!("UnaryOperation({:?}, {})", op, rhs.get().repr())
            }
            ParseNode::BinaryOperation(op, lhs, rhs) => {
                format!(
                    "BinaryOperation({:?}, {}, {})",
                    op,
                    lhs.get().repr(),
                    rhs.get().repr()
                )
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
        caqtus_parsing_rs::ParseNode::Add(lhs, rhs) => {
            ParseNode::BinaryOperation(
                BinaryOperator::Plus,
                Py::new(py, convert(py, *lhs)).unwrap(),
                Py::new(py, convert(py, *rhs)).unwrap(),
            )
        }
        caqtus_parsing_rs::ParseNode::Subtract(lhs, rhs) => {
            ParseNode::BinaryOperation(
                BinaryOperator::Minus,
                Py::new(py, convert(py, *lhs)).unwrap(),
                Py::new(py, convert(py, *rhs)).unwrap(),
            )
        }
        caqtus_parsing_rs::ParseNode::Multiply(lhs, rhs) => {
            ParseNode::BinaryOperation(
                BinaryOperator::Times,
                Py::new(py, convert(py, *lhs)).unwrap(),
                Py::new(py, convert(py, *rhs)).unwrap(),
            )
        }
        caqtus_parsing_rs::ParseNode::Divide(lhs, rhs) => {
            ParseNode::BinaryOperation(
                BinaryOperator::Div,
                Py::new(py, convert(py, *lhs)).unwrap(),
                Py::new(py, convert(py, *rhs)).unwrap(),
            )
        }
        caqtus_parsing_rs::ParseNode::Negate(rhs) => {
            ParseNode::UnaryOperation(
                UnaryOperator::Neg,
                Py::new(py, convert(py, *rhs)).unwrap(),
            )
        }
        caqtus_parsing_rs::ParseNode::Power(lhs, rhs) => {
            ParseNode::BinaryOperation(
                BinaryOperator::Pow,
                Py::new(py, convert(py, *lhs)).unwrap(),
                Py::new(py, convert(py, *rhs)).unwrap(),
            )
        }
        caqtus_parsing_rs::ParseNode::Call(name, args) => {
            ParseNode::Call {
                name,
                args: args
                    .into_iter()
                    .map(|arg| Py::new(py, convert(py, arg)).unwrap())
                    .collect(),
            }
        }
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
