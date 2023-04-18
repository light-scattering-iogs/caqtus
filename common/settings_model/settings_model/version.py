import semver


class Version(semver.Version):
    @classmethod
    def _parse(cls, version):
        if isinstance(version, str):
            return cls.parse(version)
        elif isinstance(version, cls):
            return version
        else:
            raise TypeError(f"Cannot parse version from {version}")

    @classmethod
    def __get_validators__(cls):
        yield cls._parse
