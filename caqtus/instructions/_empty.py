class Empty:
    def __eq__(self, other):
        return isinstance(other, Empty)
