import enum


class DataType(enum.Enum):
    """Enumeration for the type of data attached to a shot.

    Each value stored in the database is tagged with a data type. This represents how
    the data was generated for this shot and how it should be interpreted.

    Attributes:
        PARAMETER: The data is a value that was used to configure a shot. A shot can be
            understood as a function that takes a set of parameters and returns a set of
            measurements.
        MEASURE: The data is a measurement that was recorded during a shot. A shot can
            acquire multiple measurements such as the fluorescence of the MOT, an image,
            the presence of an atom, etc.
        ANALYSIS: The data is a value that was computed from one or more measurements.
        SCORE: This is used for optimization. It indicates the value of a score function
            for a given set of parameters.
    """

    PARAMETER = "parameter"
    MEASURE = "measure"
    ANALYSIS = "analysis"
    SCORE = "score"
