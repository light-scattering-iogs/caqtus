class Proxy[T]:
    def __init__(self, pid: int, obj_id: int):
        self._pid = pid
        self._obj_id = obj_id

    def __repr__(self):
        return f"Proxy(pid={self._pid}, obj_id={self._obj_id})"
