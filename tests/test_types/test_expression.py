from caqtus.types.expression import Expression, expression_builtins, DEFAULT_BUILTINS


def test_default_builtins():
    expr = Expression("pi")
    assert expr.evaluate({}) == DEFAULT_BUILTINS["pi"]


def test_builtins_override():
    token = expression_builtins.set({**DEFAULT_BUILTINS, "pi": 42})
    try:
        expr = Expression("pi")
        assert expr.evaluate({}) == 42
    finally:
        expression_builtins.reset(token)
