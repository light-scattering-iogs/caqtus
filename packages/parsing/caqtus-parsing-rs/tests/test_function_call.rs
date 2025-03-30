use caqtus_parsing_rs::parse;

#[test]
fn test_can_parse_function_call() {
    assert_eq!(parse("f(1, 2, 3)").unwrap().to_string(), "f(1, 2, 3)");
    assert_eq!(parse("a.b(1,)").unwrap().to_string(), "a.b(1)");
}

#[test]
fn test_can_parse_call_with_subexpr_args() {
    assert_eq!(parse("f(1 + 2, 3 * 4)").unwrap().to_string(), "f((1 + 2), (3 * 4))");
    assert_eq!(parse("f(12 MHz)").unwrap().to_string(), "f(12 MHz)");
    assert_eq!(parse("f(sqrt(2))").unwrap().to_string(), "f(sqrt(2))");
    assert_eq!(parse("square_wave((t- 10 ms) / 1 ms)").unwrap().to_string(), "square_wave(((t - 10 ms) / 1 ms))");
}

#[test]
fn test_call_priority() {
    assert_eq!(parse("f(1) + g(2)").unwrap().to_string(), "(f(1) + g(2))");
    assert_eq!(parse("f(1) - g(2)").unwrap().to_string(), "(f(1) - g(2))");
    assert_eq!(parse("f(1) * g(2)").unwrap().to_string(), "(f(1) * g(2))");
    assert_eq!(parse("f(1) / g(2)").unwrap().to_string(), "(f(1) / g(2))");
    assert_eq!(parse("f(1) ^ g(2)").unwrap().to_string(), "(f(1) ^ g(2))");
}
