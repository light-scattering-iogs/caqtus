from NodeGraphQt import BaseNode


class OutputNode(BaseNode):
    __identifier__ = "caqtus.sequencer_node"
    NODE_NAME = "Output"

    def __init__(self):
        super().__init__()
        self.add_input("in", display_name=False, multi_input=False)
