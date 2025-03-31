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
            ) => op_a == op_b && lhs_a.get() == lhs_b.get() && rhs_a.get() == rhs_b.get(),
            (
                ParseNode::UnaryOperation {
                    operator: op_a,
                    operand: rhs_a,
                },
                ParseNode::UnaryOperation {
                    operator: op_b,
                    operand: rhs_b,
                },
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
                format!("Quantity({}, \"{}\")", value, unit)
            }
            ParseNode::Identifier { name } => format!("Identifier(\"{}\")", name),
            ParseNode::UnaryOperation { operator, operand } => {
                format!("UnaryOperation({:?}, {})", operator, operand.get().repr())
            }
            ParseNode::BinaryOperation { operator, lhs, rhs } => {
                format!(
                    "BinaryOperation({:?}, {}, {})",
                    operator,
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
                format!("Call(\"{}\", [{}])", name, args_str)
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
        caqtus_parsing_rs::ParseNode::Add(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Plus,
            lhs: Py::new(py, convert(py, *lhs)).unwrap(),
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Subtract(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Minus,
            lhs: Py::new(py, convert(py, *lhs)).unwrap(),
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Multiply(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Times,
            lhs: Py::new(py, convert(py, *lhs)).unwrap(),
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Divide(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Div,
            lhs: Py::new(py, convert(py, *lhs)).unwrap(),
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Power(lhs, rhs) => ParseNode::BinaryOperation {
            operator: BinaryOperator::Pow,
            lhs: Py::new(py, convert(py, *lhs)).unwrap(),
            rhs: Py::new(py, convert(py, *rhs)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Negate(operant) => ParseNode::UnaryOperation {
            operator: UnaryOperator::Neg,
            operand: Py::new(py, convert(py, *operant)).unwrap(),
        },
        caqtus_parsing_rs::ParseNode::Call(name, args) => ParseNode::Call {
            name,
            args: args
                .into_iter()
                .map(|arg| Py::new(py, convert(py, arg)).unwrap())
                .collect(),
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
