from caqtus.gui.qtutil import QtAsyncio
from caqtus.session import ParameterNamespace
from caqtus.types.expression import Expression
from .session_maker import session_maker


def test_0(session_maker):
    async def f():
        async with session_maker.async_session() as session:
            p1 = ParameterNamespace.from_mapping({"a": Expression("1")})
            await session.set_global_parameters(parameters=p1)
            p2 = await session.get_global_parameters()
            assert p1 == p2

    QtAsyncio.run(f(), keep_running=False)
