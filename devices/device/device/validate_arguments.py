import pydantic


class _Config:
    arbitrary_types_allowed = True

validate_arguments = pydantic.validate_arguments(config=_Config)
