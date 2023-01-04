from concurrent.futures import ThreadPoolExecutor, Executor


class SequenceContext:
    def __init__(self, variables: dict[str]):
        self.variables = variables
        self.delayed_executor: Executor = ThreadPoolExecutor()
        self.shot_numbers: dict[str, int] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delayed_executor.shutdown(wait=True)
