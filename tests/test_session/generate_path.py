import hypothesis.strategies

from caqtus.session import PureSequencePath
from caqtus.session._path import _PATH_NAME_REGEX

path_name = hypothesis.strategies.from_regex(_PATH_NAME_REGEX)
path_parts = hypothesis.strategies.lists(path_name, min_size=0, max_size=5)
path = hypothesis.strategies.builds(PureSequencePath.from_parts, path_parts)
