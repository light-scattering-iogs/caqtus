mod lexer;
mod parser;

pub use crate::parser::{parse, ParseNode, BinaryOperator, UnaryOperator};

extern crate uom;

use uom::fmt::DisplayStyle::*;
use uom::si::f32::*;
use uom::si::length::meter;

#[cfg(test)]
mod tests {
    use chumsky::span::SimpleSpan;
    use quantities::prelude::*;
    use super::*;
    #[test]
    fn test_units() {

        let mut l1 = Length::new::<meter>(15.0);
        for i in 0..10 {
            let l1 = l1 * Length::new::<meter>(15.0);
        }
        println!("{:?}", l1);
    }
}
