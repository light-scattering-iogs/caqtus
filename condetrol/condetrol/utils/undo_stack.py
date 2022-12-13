class UndoStack:
    def __init__(self):
        self._stack: list = []
        self._undo_level: int = -1

    def push(self, state) -> None:
        self._stack = self._stack[: self._undo_level + 1]
        self._stack.append(state)
        self._undo_level += 1

    def undo(self):
        if self._undo_level < 0:
            raise RuntimeError("Nothing has been pushed to the undo/redo stack")
        if self._undo_level > 0:
            self._undo_level -= 1
        return self._stack[self._undo_level]

    def redo(self):
        if self._undo_level < 0:
            raise RuntimeError("Nothing has been pushed to the undo/redo stack")

        if self._undo_level + 1 < len(self._stack):
            self._undo_level += 1
        return self._stack[self._undo_level]
