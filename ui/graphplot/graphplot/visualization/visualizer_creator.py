from __future__ import annotations

import abc
from typing import Optional

import polars
from PyQt6.QtWidgets import QWidget

import qabc


class VisualizerCreator(qabc.QABC):
    @abc.abstractmethod
    def create_visualizer(self) -> Visualizer:
        raise NotImplementedError()


class Visualizer(QWidget, qabc.QABC):
    @abc.abstractmethod
    def update_data(self, dataframe: Optional[polars.DataFrame]) -> None:
        raise NotImplementedError()
