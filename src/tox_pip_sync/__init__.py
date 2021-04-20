import pluggy
from tox.reporter import verbosity0

from tox_pip_sync._pip_sync import pip_sync

hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_configure(config):
    """Called after command line options are parsed and ini-file has been read."""


@hookimpl
def tox_runenvreport(venv, action):
    """Get the installed packages and versions in this venv."""

    # This appears to be purely FYI, and just slows things down
    return ["*** listing modules disabled by tox-pip-sync ***"]


@hookimpl
def tox_testenv_install_deps(venv, action):
    """Perform install dependencies action for this venv."""

    # Call our pip sync method instead of the usual way to install dependencies
    verbosity0("Syncing virtual env with pip-sync")
    pip_sync(venv, action)
    venv.pip_synced = True

    # Let tox know we've handled this case
    return True


@hookimpl
def tox_runtest_pre(venv):
    """Perform arbitrary action after running tests for this venv."""

    if not getattr(venv, "pip_synced", False):
        # `tox_testenv_install_deps` does not get called every time we run tox
        # so assuming we've not run before, we should make sure we have
        tox_testenv_install_deps(venv=venv, action=venv.new_action("pip-sync"))