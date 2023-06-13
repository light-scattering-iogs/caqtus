import logging

import numpy
import numpy as np
from parse_optimization import parse_shots, get_parser

from analyza_obsolete.import_data import (
    build_dataframe_from_shots,
    import_all,
    array_as_float,
    apply
)
from experiment.session import get_standard_experiment_session
from sequence.runtime import Shot

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

session = get_standard_experiment_session()


def main():
    parser = get_parser()

    args = parser.parse_args()
    print("READY")

    while shots := parse_shots(input()):
        score = compute_score(shots)
        print(f"SCORE {score}")


def compute_score(shots: list[Shot]) -> float:
    roi = (slice(70, 120), slice(90, 140))
    data = build_dataframe_from_shots(
        shots,
        import_all
        | array_as_float
        | apply(
            lambda image, background: numpy.sum(image[roi] - background[roi]) * 0.11,
            ["Orca Quest.picture", "Orca Quest.background"],
            "fluo",
        ),
        session,
    )

    return data["fluo"].mean()


if __name__ == "__main__":
    main()
