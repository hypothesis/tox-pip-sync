import toml


def load_config(project_dir):
    """Load our config for a particular project."""

    project_file = project_dir / "pyproject.toml"
    if not project_file.exists():
        return {}

    toml_config = toml.load(project_file)

    try:
        return toml_config["tool"]["tox"]["tox_pip_sync"]
    except KeyError:
        return {}
