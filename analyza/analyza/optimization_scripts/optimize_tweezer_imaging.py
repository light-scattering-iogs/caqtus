import logging

import numpy as np

from analyza.import_data import (
    build_dataframe_from_sequence,
    build_dataframe_from_shots,
    import_all,
    array_as_float,
)
from analyze_spots import SpotAnalyzer
from experiment.session import get_standard_experiment_session
from parse_optimization import parse_shots, get_parser
from sequence.runtime import Sequence, Shot

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

session = get_standard_experiment_session()


def main():
    """Compute the fluorescence signal over noise ratio for tweezers"""

    parser = get_parser()
    parser.add_argument(
        "reference_sequence_path",
        type=str,
        help="Path to the reference sequence that is used to find the traps.",
    )
    args = parser.parse_args()
    spot_analyzer = create_spot_analyzer(Sequence(args.reference_sequence_path))

    while shots := parse_shots(input()):
        print(compute_cost(shots, spot_analyzer))


def create_spot_analyzer(reference_sequence: Sequence) -> SpotAnalyzer:
    logger.info(f"Loading reference sequence {reference_sequence.path}")
    data = build_dataframe_from_sequence(
        reference_sequence,
        import_all | array_as_float,
        session,
    )
    data["Orca Quest.picture"] -= data["Orca Quest.background"]
    image = data["Orca Quest.picture"].mean()
    spots_analyzer = SpotAnalyzer()
    spots_analyzer.register_regions_of_interest(image, 0.2, 2)
    logger.info(f"Found {spots_analyzer.number_spots} traps")
    return spots_analyzer


def compute_cost(shots: list[Shot], spot_analyzer: SpotAnalyzer) -> float:
    data = build_dataframe_from_shots(
        shots,
        import_all | array_as_float,
        session,
    )
    data["Orca Quest.picture"] -= data["Orca Quest.background"]

    individual_fluos = data["Orca Quest.picture"].apply(
        lambda image: spot_analyzer.compute_intensity(image * 0.11, method=np.sum)
    )
    for trap in range(spot_analyzer.number_spots):
        data[f"fluo_{trap}"] = individual_fluos.apply(lambda fluos: fluos[trap])

    data["fluo"] = (
        sum(data[f"fluo_{trap}"] for trap in range(spot_analyzer.number_spots))
        / spot_analyzer.number_spots
    )
    return data["fluo"].mean() / data["fluo"].std()


if __name__ == "__main__":
    main()
