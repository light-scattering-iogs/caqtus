from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Optional

from util import attrs, serialization


@attrs.define
class Step(ABC):
    _parent: Optional["Step"] = attrs.field(
        on_setattr=attrs.setters.validate,
    )
    _children: list["Step"] = attrs.field(
        converter=list,
        on_setattr=attrs.setters.convert,
    )

    def __init__(
        self,
        parent: Optional["Step"] = None,
        children: Optional[Iterable["Step"]] = None,
    ):
        self._parent = None
        self._children = []

        self.parent = parent
        if children is not None:
            self.children = list(children)
        else:
            self.children = []

    @property
    def parent(self) -> Optional["Step"]:
        return self._parent

    @parent.setter
    def parent(self, new_parent: Optional["Step"]):
        if self.parent is not new_parent:
            self._check_loop(new_parent)
            self._detach(self.parent)
            self._attach(new_parent)

    #
    def _check_loop(self, parent: Optional["Step"]):
        if parent is not None:
            if any(ancestor is self for ancestor in parent.iter_path_reverse()):
                raise ValueError(
                    f"Cannot set parent. {self} would be ancestor of itself."
                )

    def _detach(self, parent: Optional["Step"]):
        if parent is not None:
            assert any(child is self for child in parent._children), "Tree is corrupt."
            parent._children = [
                child for child in parent._children if child is not self
            ]
            self._parent = None

    def _attach(self, parent: Optional["Step"]):
        if parent is not None:
            assert not any(
                child is self for child in parent._children
            ), "Tree is corrupt."
            parent._children.append(self)
            self._parent = parent

    def iter_path_reverse(self) -> Iterable["Step"]:
        node = self
        while node is not None:
            yield node
            node = node.parent

    @property
    def children(self) -> tuple["Step"]:
        return tuple(self._children)

    @children.setter
    def children(self, children: Iterable["Step"]):
        new_children = tuple(children)
        self._check_children_unique(new_children)
        old_children = self.children
        del self.children
        try:
            for child in new_children:
                child.parent = self
            assert len(self.children) == len(new_children)
        except Exception:
            self.children = old_children
            raise

    @staticmethod
    def _check_children_unique(children: Iterable["Step"]):
        seen = set()
        for child in children:
            if not isinstance(child, Step):
                raise TypeError(
                    f"Cannot add non-node object {child}. It is not a subclass of <Step>."
                )
            child_id = id(child)
            if child_id not in seen:
                seen.add(child_id)
            else:
                raise ValueError(f"Cannot add node {child} multiple times as child.")

    @children.deleter
    def children(self):
        for child in self.children:
            child.parent = None
        assert len(self.children) == 0

    @property
    def is_root(self):
        return self.parent is None

    def row(self):
        if self.is_root:
            return 0
        else:
            for i, child in enumerate(self.parent.children):
                if child is self:
                    return i

    @abstractmethod
    def expected_number_shots(self) -> Optional[int]:
        """Return the number of shots planned inside this step

        Returns None if this is unknown.
        """
        raise NotImplementedError()

    @abstractmethod
    def __eq__(self, other):
        raise NotImplementedError()


# (De)-serializing steps is difficult because this is a recursive data structure, and
# we need to be able to serialize and deserialize subclasses of Step. I didn't manage to do this with the builtins hooks
# of cattrs, so I registered custom hooks for each subclass of Step. That means that if you add a new subclass of Step,
# you need to update the structure hook for Step and implement the (un)structure hook for the new subclass.


def unstructure_step(step: Step) -> dict:
    # To unstructure a step, we return the dictionary with the specific keys of the subclass and add the key
    # "step_type" with the name of the subclass as value.

    return serialization.unstructure(step, type(step)) | {
        "step_type": str(type(step).__name__)
    }


serialization.register_unstructure_hook(Step, unstructure_step)


def structure_hook(data: dict, cls: type[Step]) -> Step:
    # To reconstruct a step with the correct type, we match the key "step_type" to the subclass of Step.
    target_subclass = data["step_type"]
    from .sequence_steps import SequenceSteps
    from .variable_declaration import VariableDeclaration
    from .execute_shot import ExecuteShot
    from .arange_loop import ArangeLoop
    from .linspace_loop import LinspaceLoop

    step_types = {
        SequenceSteps.__name__: SequenceSteps,
        VariableDeclaration.__name__: VariableDeclaration,
        ExecuteShot.__name__: ExecuteShot,
        ArangeLoop.__name__: ArangeLoop,
        LinspaceLoop.__name__: LinspaceLoop,
    }
    return serialization.structure(data, step_types[target_subclass])


serialization.register_structure_hook(Step, structure_hook)


def compute_total_number_shots(steps: Iterable[Step]) -> Optional[int]:
    result = 0
    for step in steps:
        step_result = step.expected_number_shots()
        if step_result is None:
            return None
        result += step_result
    return result
