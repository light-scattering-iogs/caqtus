from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

NodeType = TypeVar("NodeType")


class TreeNode(Generic[NodeType], ABC):
    """Abstract class meant to represent a tree

    It is meant to be subclassed for a specific data type and used for a Qt tree model
    """
    def __init__(
        self, data: list[NodeType] | NodeType, parent: "Optional[TreeNode[NodeType]]" = None, row=0
    ):
        self.parent: Optional[TreeNode] = parent
        self.internal_pointer: list[NodeType] | NodeType = data
        self.row = row
        self.children: Optional[list[TreeNode[NodeType]]] = self.get_children()

    @abstractmethod
    def get_children(self) -> "list[TreeNode[NodeType]]":
        pass

    @abstractmethod
    def update_value(self, new_value: NodeType):
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
