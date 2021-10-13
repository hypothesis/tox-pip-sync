import json
import os
from functools import lru_cache
from glob import glob
from os.path import relpath
from pathlib import Path

from tox.reporter import verbosity1

from tox_pip_sync._requirements import RequirementList


def pip_sync(venv, action, skip_on_hash_match=True):
    """Use pip-sync to ensure requirements are up to date in a virtual env."""

    requirements = RequirementList.from_strings(
        (dep.name for dep in venv.envconfig.deps)
    )
    current_hash = requirements.hash(root_dir=venv.envconfig.config.setupdir)
    env_data = EnvData(venv.path)

    if skip_on_hash_match:
        last_hash = env_data.last_hash
        if last_hash == current_hash:
            verbosity1("Skipping pip-sync, as hash has not changed")
            return

    pip_tools_run(
        "pip-sync",
        list(requirements_files_for_env(venv, action, requirements)),
        message="Syncing virtual env with pip-sync",
        venv=venv,
        action=action,
    )

    # Store the results of this run
    env_data.save(requirements_hash=current_hash)


def pip_tools_run(exe_name, arguments, message, venv, action):
    """Run a pip-tools executable with arguments in a virtual env."""

    exe_path = venv.envconfig.envbindir / exe_name

    if not exe_path.exists():
        verbosity1("Bootstrapping pip-tools")
        # pylint: disable=protected-access
        # Use `--force` to ensure `pip-tools` is in our virtual env and not
        # being picked up via `--sitepackages`
        venv._install(["pip-tools", "--force"], action=action)

        assert exe_path.exists(), (
            f"Expected executable '{exe_path}' was not installed "
            "as a result of installing `pip-tools`"
        )

    action.setactivity(exe_name, message)
    verbosity1(
        # pylint: disable=protected-access
        venv._pcall(
            [exe_path] + arguments,
            cwd=venv.envconfig.config.toxinidir,
            action=action,
        )
    )


def requirements_files_for_env(venv, action, requirements):
    """Return requirements files for a tox virtual env.

    This will read, create or invent them as necessary to provide files for
    `pip-sync` to work with.
    """

    for req in requirements:
        # Yield out any requirements like '-r filename.txt'. We'll assume they
        # are already compiled for us
        if req.arg_type == req.ArgType.REFERENCE:
            yield req.filename

    if requirements.needs_compilation:
        yield _pinned_file_for_requirements(venv, action, requirements)


def _pinned_file_for_requirements(venv, action, requirements):
    requirements_hash = requirements.hash(root_dir=venv.envconfig.config.setupdir)
    stub = "tox-pip-sync_" + requirements_hash

    pinned = venv.path / stub + ".txt"
    if pinned.exists():
        verbosity1(f"Using existing compiled dependencies: '{pinned}'")
        return pinned

    # We can't find what we're looking for, so clear out any stale files
    clear_compiled_files(venv)

    # Create a new version and compile it
    relative_root = Path(relpath(venv.envconfig.config.setupdir, venv.path))
    constrained = requirements.constrained_set(relative_root)
    unpinned = venv.path / stub + ".in"
    unpinned.write_text("\n".join(str(dep) for dep in constrained), encoding="utf-8")

    pip_tools_run(
        "pip-compile",
        [str(unpinned)],
        message=f"Compiling dependencies '{constrained}'",
        venv=venv,
        action=action,
    )

    if not pinned.exists():
        raise FileNotFoundError(pinned)

    return str(pinned)


def clear_compiled_files(venv):
    """Remove any files created by `tox-pip-sync`."""

    # We can't find what we're looking for, so clear out any stale files
    for old_files in glob(str(venv.path / "tox-pip-sync_*")):
        os.remove(old_files)


class EnvData:
    """Class for accessing data stored in a testenv by and for tox-pip-sync."""

    def __init__(self, venv_path):
        """Initialize an EnvData object.

        :param venv_path: The path to the root of the virtual env.
        """
        self.path = venv_path / "tox-pip-sync.json"

    @property
    def last_hash(self):
        """Get the last hash stored in the data."""

        return self._load().get("hash")

    def save(self, requirements_hash):
        """Save the hash."""

        self.path.write_text(json.dumps({"hash": requirements_hash}), encoding="utf-8")

    @lru_cache(1)
    def _load(self):
        if not self.path.exists():
            return {}

        return json.loads(self.path.read_text(encoding="utf-8"))
