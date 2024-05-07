from caqtus.gui.condetrol import Condetrol
from ._extension import _extension
from ._session_maker import get_session_maker
from ._experiment_manager import get_experiment_manager


def launch_condetrol():
    app = Condetrol(
        get_session_maker(),
        connect_to_experiment_manager=get_experiment_manager,
        extension=_extension.condetrol_extension,
    )
    app.run()
