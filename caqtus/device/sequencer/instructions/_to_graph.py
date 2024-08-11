import functools
from typing import Optional

import graphviz
import numpy as np

from ._instructions import SequencerInstruction, Concatenated, Repeated, Pattern


def to_graph(instruction: SequencerInstruction) -> graphviz.Digraph:
    """Convert a sequencer instruction to a graphiz graph for visualization.

    This function requires `Graphviz <https://www.graphviz.org/>`_ to be installed and
    available in the system path.

    Args:
        instruction: The instruction to convert to a graph.

    Returns:
        The graph representation of the instruction.
    """

    graph = graphviz.Digraph(graph_attr={"ordering": "in"})
    add_to_graph(instruction, graph, [0])
    return graph


def levels_to_str(levels: list[int], port: Optional[str] = None) -> str:
    value = "_".join(map(str, levels))
    if port is not None:
        value += f":{port}"
    return value


@functools.singledispatch
def add_to_graph(instr, graph, levels: list[int]) -> None:
    raise NotImplementedError(f"Cannot add {type(instr)} to graph")


@add_to_graph.register
def _(instr: Concatenated, graph, levels: list[int]):
    graph.node(levels_to_str(levels), "+", shape="circle")
    graph.attr(rank="same")
    for i, sub_instr in enumerate(instr.instructions):
        add_to_graph(sub_instr, graph, levels + [i])
        if isinstance(sub_instr, Pattern):
            port = "port"
        else:
            port = None
        graph.edge(levels_to_str(levels), levels_to_str(levels + [i], port))
    return graph


@add_to_graph.register
def _(instr: Repeated, graph, levels: list[int]):
    graph.node(levels_to_str(levels), f"*{instr.repetitions}", shape="circle")
    add_to_graph(instr.instruction, graph, levels + [0])
    if isinstance(instr.instruction, Pattern):
        port = "port"
    else:
        port = None
    graph.edge(levels_to_str(levels), levels_to_str(levels + [0], port))


@add_to_graph.register
def _(instr: Pattern, graph, levels: list[int]):
    graph.attr(shape="plain")

    rows = []

    if instr.dtype.names is None:
        cells = values_to_row(instr.array, port="port")
        rows.append(f"<TR>{'\n'.join(cells)}</TR>")
    else:
        for i, name in enumerate(instr.dtype.names):
            cells = values_to_row(instr.array[name])
            if i == 0:
                cells = [f'<TD PORT="port"><B>{name}</B></TD>'] + cells
            else:
                cells = [f"<TD><B>{name}</B></TD>"] + cells
            rows.append(f"<TR>{'\n'.join(cells)}</TR>")

    label = (
        f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">'
        f"{'\n'.join(rows)}"
        f"</TABLE>>"
    )

    graph.node(levels_to_str(levels), label, shape="plain")
    return graph


def values_to_row(values: np.ndarray, port: Optional[str] = None) -> list[str]:
    if values.dtype == np.bool_:
        values = values.astype(int)
    cells = [f"<TD>{v}</TD>" for v in values]
    if port is not None:
        if cells:
            cells[0] = f'<TD PORT="{port}">{values[0]}</TD>'
    return cells
