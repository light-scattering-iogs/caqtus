use pyo3::pyclass;

#[pyclass]
pub enum ParameterType {
    Boolean(),
    Integer(),
    Float(),
    Quantity { unit: String },
}