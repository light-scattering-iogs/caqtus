from caqtus.session._exception_summary import TracebackSummary


def test():
    try:
        raise RuntimeError("err 1") from RuntimeError("err 1 cause")
    except RuntimeError as e:
        err1 = e
    try:
        raise RuntimeError("err 2 context")
    except RuntimeError:
        try:
            raise RuntimeError("err 2")
        except RuntimeError as e:
            err2 = e

    exception = ExceptionGroup("group", [err1, err2])

    t = TracebackSummary.from_exception(exception)

    print(t)

    assert t == TracebackSummary(
        exc_type="builtins.ExceptionGroup",
        exc_msg="group (2 sub-exceptions)",
        notes=None,
        cause=None,
        context=None,
        exceptions=[
            TracebackSummary(
                exc_type="builtins.RuntimeError",
                exc_msg="err 1",
                notes=None,
                cause=TracebackSummary(
                    exc_type="builtins.RuntimeError",
                    exc_msg="err 1 cause",
                    notes=None,
                    cause=None,
                    context=None,
                    exceptions=None,
                ),
                context=None,
                exceptions=None,
            ),
            TracebackSummary(
                exc_type="builtins.RuntimeError",
                exc_msg="err 2",
                notes=None,
                cause=None,
                context=TracebackSummary(
                    exc_type="builtins.RuntimeError",
                    exc_msg="err 2 context",
                    notes=None,
                    cause=None,
                    context=None,
                    exceptions=None,
                ),
                exceptions=None,
            ),
        ],
    )
