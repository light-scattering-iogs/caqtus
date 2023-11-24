from __future__ import annotations

import abc
from typing import Optional

import pandas
from PyQt6.QtWidgets import QWidget

import qabc


class VisualizerCreator(QWidget, qabc.QABC):
    @abc.abstractmethod
    def create_visualizer(self) -> Visualizer:
        raise NotImplementedError()


class Visualizer(QWidget, qabc.QABC):
    @abc.abstractmethod
    def update_data(self, dataframe: Optional[pandas.DataFrame]) -> None:
        raise NotImplementedError()
