from configparser import ConfigParser

import toml

TYPED_OPTIONS = {
    # Option name:  (type, default)
    "skip_listing": (bool, True)
}


def load_config(project_dir):
    """Load our config for a particular project."""

    config = IniConfig.parse(project_dir / "tox.ini")
    config.update(_parse_toml(project_dir))

    return config


def _parse_toml(project_dir):
    project_file = project_dir / "pyproject.toml"
    if not project_file.exists():
        return {}

    toml_config = toml.load(project_file)

    try:
        return toml_config["tool"]["tox"]["tox_pip_sync"]
    except KeyError:
        return {}


class IniConfig:
    """Load settings from a tox.ini file."""

    # pylint: disable=too-few-public-methods

    @classmethod
    def parse(cls, file_name):
        """Load settings from a tox.ini file."""

        parser = ConfigParser()
        parser.read(file_name)

        if "tox_pip_sync" not in parser:
            return {}

        values = dict(parser["tox_pip_sync"])
        cls._coerce_values(values)

        return values

    @classmethod
    def _coerce_values(cls, values):
        # TOML has sane type handling, so this is only necessary for INI files
        for key, (target_type, default) in TYPED_OPTIONS.items():
            if key in values:
                values[key] = cls._convert_ini_type(values[key], target_type, default)

    @classmethod
    def _convert_ini_type(cls, value, target_type, default):
        if target_type == bool:
            # This is handy data, but no nice way to access them as we want to
            # We don't want to deal with `ConfigParser`'s section objects.
            return ConfigParser.BOOLEAN_STATES.get(value, default)

        return value  # pragma: no cover
