from util.run_on_change_only import RunOnChangeDescriptor
from util.run_on_change_only import run_on_change_method


def test_run_on_change_only():
    class Test:
        @run_on_change_method
        def func(self, x):
            return x

    assert isinstance(Test.func, RunOnChangeDescriptor)
    test = Test()
    assert test.func is test.func
    assert test.func([1, 2]) == [1, 2]
    assert 1 == 1.0
    assert test.func(1) is test.func(1.0)

    t1 = Test()
    assert t1.func(1.0) is not test.func(1.0)
