import copy
import logging
import subprocess
import threading
import time
from queue import Queue, Empty
from typing import Union, Optional

from bayes_opt import BayesianOptimization, UtilityFunction

from experiment.configuration import OptimizerConfiguration
from parse_optimization import write_shots
from sequence.configuration import OptimizationVariableInfo
from sequence.runtime import Shot, Sequence
from units import Quantity

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

AnalogValues = Union[float | Quantity]  # type: ignore


class Optimizer:
    def __init__(
        self,
        optimization_variables: list[OptimizationVariableInfo],
        context_variables: dict,
    ):
        self._optimization_variables = optimization_variables
        self._context_variables = copy.deepcopy(context_variables)
        self._bounds = evaluate_optimization_bounds(
            self._optimization_variables, self._context_variables
        )

        self._initial_values = evaluate_initial_values(
            self._optimization_variables, self._context_variables
        )

        for variable_name, initial_value in self._initial_values.items():
            minimum, maximum = self._bounds[variable_name]
            if not (minimum <= initial_value <= maximum):
                raise ValueError(
                    f"Initial value {initial_value} for variable {variable_name} is not in the range "
                    f"[{minimum}, {maximum}]"
                )

        # noinspection PyTypeChecker
        self._optimizer = BayesianOptimization(
            f=None,
            pbounds=self.convert_bounds_to_float(self._bounds),
            allow_duplicate_points=True,
        )
        self._utility_function = UtilityFunction(kind="ucb", kappa=2.5, xi=0)
        self._optimizer.set_gp_params(alpha=0.1)
        self._first_time_called = True
        self._optimizer.probe(self.convert_to_float(self._initial_values), lazy=True)

    def suggest_values(self) -> dict[str, AnalogValues]:
        if self._first_time_called:
            self._first_time_called = False
            return self._initial_values
        else:
            raw_values = self._optimizer.suggest(self._utility_function)
            return self.convert_to_quantity(raw_values)

    def register(self, values: dict[str, AnalogValues], score: float):
        self._optimizer.register(params=self.convert_to_float(values), target=score)

    def convert_to_float(self, values: dict[str, AnalogValues]) -> dict[str, float]:
        result = {}
        for variable_name, initial_value in self._initial_values.items():
            value = values[variable_name]
            if isinstance(initial_value, Quantity):
                if not isinstance(value, Quantity):
                    raise ValueError(
                        f"Value for variable {variable_name} must have units {initial_value.units}"
                    )
                value = value.to(initial_value.units).magnitude
            result[variable_name] = value
        return result

    def convert_bounds_to_float(
        self, bounds: dict[str, tuple[AnalogValues, AnalogValues]]
    ) -> dict[str, tuple[float, float]]:
        minimums = {bound_name: bound[0] for bound_name, bound in bounds.items()}
        maximums = {bound_name: bound[1] for bound_name, bound in bounds.items()}

        minimums = self.convert_to_float(minimums)
        maximums = self.convert_to_float(maximums)

        return {
            bound_name: (minimums[bound_name], maximums[bound_name])
            for bound_name in minimums
        }

    def convert_to_quantity(self, values: dict[str, float]) -> dict[str, AnalogValues]:
        result = {}
        for variable_name, initial_value in self._initial_values.items():
            value = values[variable_name]
            if isinstance(initial_value, Quantity):
                value = value * initial_value.units
            result[variable_name] = value
        return result


def evaluate_optimization_bounds(
    optimization_variables: list[OptimizationVariableInfo],
    context_variables: dict,
) -> dict[str, tuple[AnalogValues, AnalogValues]]:
    bounds = {}
    for variable in optimization_variables:
        name = variable["name"]
        first_bound = variable["first_bound"].evaluate(context_variables)
        second_bound = variable["second_bound"].evaluate(context_variables)
        minimum = min(first_bound, second_bound)
        maximum = max(first_bound, second_bound)
        bounds[name] = (minimum, maximum)
    return bounds


def evaluate_initial_values(
    optimization_variables: list[OptimizationVariableInfo], context_variables: dict
) -> dict[str, AnalogValues]:
    return {
        variable["name"]: variable["initial_value"].evaluate(context_variables)
        for variable in optimization_variables
    }


class CostEvaluatorProcess:
    """Evaluate the cost of a series of shot by running an evaluation script in a subprocess.

    The script is expected to read the shots from stdin and write the cost to stdout. When the script is launched, it
    must output the string "READY" to indicate that it is ready to receive shots.
    """

    def __init__(
        self,
        sequence: Sequence,
        optimizer_config: OptimizerConfiguration,
    ):
        self._optimizer_config = optimizer_config
        self._sequence = sequence
        self._evaluation_process: Optional[subprocess.Popen] = None
        self._stdout_queue: Queue[str] = Queue()
        self._read_stdout_thread = threading.Thread(
            target=self._read_stdout, daemon=True
        )

    def _read_stdout(self):
        for line in self._evaluation_process.stdout:
            self._stdout_queue.put(line)

    def compute_score(self, shots: tuple[Shot, ...], timeout=10) -> float:
        if not self._evaluation_process:
            raise RuntimeError("Evaluator is not running")

        string = write_shots(shots) + "\n"
        while not self._stdout_queue.empty():
            self._stdout_queue.get()
        self._evaluation_process.stdin.write(string)
        self._evaluation_process.stdin.flush()
        initial_time = time.time()
        while time.time() - initial_time < timeout:
            try:
                line = self._stdout_queue.get(timeout=timeout)
                if line.startswith("SCORE"):
                    return float(line.split(" ")[1])
                else:
                    logger.debug(
                        f"Received line from evaluation process that cannot be interpreted: {line}"
                    )
            except Empty:
                continue
        raise TimeoutError("Evaluation process did not return score in time")

    def __enter__(self):
        args = f"{self._optimizer_config.script_path} {str(self._sequence.path)} {self._optimizer_config.parameters}"
        logger.info(f"Starting evaluation process with command: {args}")
        self._evaluation_process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self._optimizer_config.working_directory,
            encoding="utf-8",
        ).__enter__()
        self._read_stdout_thread.start()
        return self

    def is_ready(self) -> bool:
        if self._evaluation_process is None:
            raise RuntimeError("Evaluator is not running")
        if self._evaluation_process.poll() is not None:
            error = self._evaluation_process.stderr.read()
            raise RuntimeError(f"Evaluation process exited unexpectedly: {error}")
        if not self._stdout_queue.empty():
            line = self._stdout_queue.get().strip()
            logger.info(f"Received line from evaluation process: {line}")
            if line == "READY":
                return True
        return False

    def interrupt(self):
        if self._evaluation_process:
            self._evaluation_process.terminate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._evaluation_process:
            self._evaluation_process.communicate("")
            self._evaluation_process.__exit__(exc_type, exc_val, exc_tb)
