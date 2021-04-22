import os
from glob import glob

from tox.reporter import verbosity1

from tox_pip_sync._requirements import RequirementList


def pip_sync(venv, action):
    """Use pip-sync to ensure requirements are up to date in a virtual env."""

    pip_tools_run(
        "pip-sync",
        list(requirements_files_for_env(venv, action)),
        message="Syncing virtual env with pip-sync",
        venv=venv,
        action=action,
    )


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


def requirements_files_for_env(venv, action):
    """Return requirements files for a tox virtual env.

    This will read, create or invent them as necessary to provide files for
    `pip-sync` to work with.
    """

    requirements = RequirementList.from_strings(
        (dep.name for dep in venv.envconfig.deps)
    )

    for req in requirements:
        # Yield out any requirements like '-r filename.txt'. We'll assume they
        # are already compiled for us
        if req.arg_type == req.ArgType.REFERENCE:
            yield req.filename

    if requirements.needs_compilation:
        yield _pinned_file_for_requirements(venv, action, requirements)


def _pinned_file_for_requirements(venv, action, requirements):
    stub = "tox-pip-sync_" + requirements.hash(root_dir=venv.envconfig.config.setupdir)

    pinned = venv.path / stub + ".txt"
    if pinned.exists():
        verbosity1(f"Using existing compiled dependencies: '{pinned}'")
        return pinned

    # We can't find what we're looking for, so clear out any stale files
    for old_files in glob(str(venv.path / "tox-pip-sync_*")):
        os.remove(old_files)

    # Create a new version and compile it
    constrained = requirements.constrained_set()
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
