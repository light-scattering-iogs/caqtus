import asyncio
import logging

import PySide6.QtAsyncio as QtAsyncio
from PySide6.QtWidgets import QApplication, QMainWindow

logger = logging.getLogger(__name__)


async def wrap(coro):
    # noinspection PyBroadException
    try:
        return await coro
    except Exception:
        logger.critical("Unhandled exception", exc_info=True)
        loop = asyncio.get_event_loop()
        loop.stop()


class GraphPlot:
    def __init__(self, *args):
        self.app = QApplication(*args)
        self.main = QMainWindow()

    def run(self):
        self.main.show()
        QtAsyncio.run()
