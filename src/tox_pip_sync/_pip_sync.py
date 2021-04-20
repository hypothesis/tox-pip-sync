import os
import re
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

LINE_START = re.compile(r"^", re.MULTILINE)


def pip_sync(venv, action):
    """Use pip-sync to ensure requirements are up to date in a virtual env."""

    with _get_requirements(venv) as requirements_files:
        # This is how tox does it internally

        # pylint: disable=protected-access
        output = venv._pcall(
            [_pip_sync_exe(venv, action)] + requirements_files,
            cwd=venv.envconfig.config.toxinidir,
            action=action,
        )

        output = LINE_START.sub("\t", output)  # Indent
        output = f"Syncing virtual env with pip-sync:\n{output}"

        action.setactivity("pip-sync", output)


def _pip_sync_exe(venv, action):
    """Get the pip-sync executable in the virtual env."""

    pip_sync_exe = venv.envconfig.envbindir / "pip-sync"

    if not pip_sync_exe.exists():
        # This should not be necessary if we were installed normally, but when
        # we are installed via --sitepackages, the pip-tools installation will
        # update the global python env, not the virtual env we want

        # pylint: disable=protected-access
        venv._install(["pip-tools", "--force"], action=action)

    if not pip_sync_exe.exists():
        raise FileNotFoundError(f"Cannot find pip-sync exe: {pip_sync_exe}")

    return str(pip_sync_exe)


@contextmanager
def _get_requirements(venv):
    """Generate requirements files for pip-sync to use."""

    temp_dependency_file = None
    requirements_files = []
    plain_dependencies = []

    for dep in venv.envconfig.deps:
        if dep.name.startswith("-r"):
            requirements_files.append(dep.name[2:])
        else:
            plain_dependencies.append(dep.name)

    if plain_dependencies:
        with NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", prefix="tox_ini_"
        ) as temp_dependency_file:
            for dep in plain_dependencies:
                temp_dependency_file.write(dep + "\n")

        requirements_files.append(temp_dependency_file.name)

    yield requirements_files

    if temp_dependency_file:
        os.unlink(temp_dependency_file.name)
