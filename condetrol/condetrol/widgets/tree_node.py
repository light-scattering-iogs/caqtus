from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

NodeType = TypeVar("NodeType")


class TreeNode(Generic[NodeType], ABC):
    def __init__(
        self, data: NodeType, parent: "Optional[TreeNode[NodeType]]" = None, row=0
    ):
        self.parent: Optional[TreeNode] = parent
        self.internal_pointer: NodeType = data
        self.children: Optional[list[TreeNode[NodeType]]] = self.get_children()
        self.row = row

    @abstractmethod
    def get_children(self) -> "list[TreeNode[NodeType]]":
        pass

    @property
    def child_count(self) -> int:
        if self.children:
            return len(self.children)
        else:
            return 0

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(data={self.internal_pointer},"
            f" parent={self.parent}, children={self.children})"
        )
