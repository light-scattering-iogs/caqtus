import hypothesis.strategies

from core.session.path import PureSequencePath, _PATH_NAME_REGEX

path_name = hypothesis.strategies.from_regex(_PATH_NAME_REGEX)
path_parts = hypothesis.strategies.lists(path_name, min_size=0)
path = hypothesis.strategies.builds(PureSequencePath.from_parts, path_parts)
