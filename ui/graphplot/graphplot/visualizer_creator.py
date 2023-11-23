from __future__ import annotations

import abc

import pandas
from PyQt6.QtWidgets import QWidget

import qabc


class VisualizerCreator(QWidget, qabc.QABC):
    @abc.abstractmethod
    def create_visualizer(self) -> Visualizer:
        raise NotImplementedError()


class Visualizer(QWidget, qabc.QABC):
    @abc.abstractmethod
    def update_data(self, dataframe: pandas.DataFrame) -> None:
        raise NotImplementedError()
