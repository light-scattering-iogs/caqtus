from typing import Optional

from PySide6 import QtWidgets, QtHelp


class HelpWidget(QtWidgets.QSplitter):
    """A widget that displays help content.

    It displays a navigation tab widget on the left and a text browser on the right.

    The navigation tab widget contains three tabs: Content, Index, and Search.

    Args:
        help_engine: The help engine that provides the help content.
            It should already be set up with the correct help files.
        parent: The parent widget of this widget.
    """

    def __init__(
        self,
        help_engine: QtHelp.QHelpEngine,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.help_engine = help_engine

        self.tab_widget = QtWidgets.QTabWidget()
        self.content_widget = self.help_engine.contentWidget()
        self.index_widget = self.help_engine.indexWidget()
        self.tab_widget.addTab(self.content_widget, "Content")
        self.tab_widget.addTab(self.index_widget, "Index")

        search_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.help_engine.searchEngine().queryWidget())
        layout.addWidget(self.help_engine.searchEngine().resultWidget())
        search_widget.setLayout(layout)
        self.help_engine.searchEngine().queryWidget().search.connect(
            self._on_search_query
        )

        self.tab_widget.addTab(search_widget, "Search")

        self.addWidget(self.tab_widget)

        self.text_browser = HelpBrowser(self.help_engine)
        self.addWidget(self.text_browser)

        self.help_engine.searchEngine().resultWidget().requestShowLink.connect(
            self.text_browser.setSource
        )

        # We could use linkActivated signal to handle links in the text browser, but
        # it only triggers when double-clicking an item.
        # So instead we react to the clicked signal of the content widget.
        self.help_engine.contentWidget().clicked.connect(self._on_content_clicked)

        self.help_engine.indexWidget().linkActivated.connect(
            self.text_browser.setSource
        )

    def _on_content_clicked(self, index):
        item = self.help_engine.contentModel().contentItemAt(index)
        self.text_browser.setSource(item.url())

    def _on_search_query(self):
        search_input = self.help_engine.searchEngine().queryWidget().searchInput()
        self.help_engine.searchEngine().search(search_input)


class HelpBrowser(QtWidgets.QTextBrowser):
    def __init__(self, helpEngine):
        super().__init__()
        self.helpEngine = helpEngine

    def loadResource(self, type, name):
        if name.scheme() == "qthelp":
            return self.helpEngine.fileData(name)
        return super().loadResource(type, name)
