import pluggy

from tox_pip_sync._config import load_config
from tox_pip_sync._pip_sync import clear_compiled_files, pip_sync

hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_configure(config):
    """Load our configuration.

    Called after command line options are parsed and ini-file has been read.
    """

    config.tox_pip_sync = load_config(config.setupdir)


@hookimpl
def tox_testenv_create(venv, action):  # pylint: disable=unused-argument
    """Perform creation action for this venv."""

    # Ensure any files we've left about are removed if the environment is being
    # re/created as we can't assume they wouldn't compile differently in the
    # new env we find ourselves.
    clear_compiled_files(venv)


@hookimpl
def tox_testenv_install_deps(venv, action):
    """Perform install dependencies action for this venv."""

    # Call our pip sync method instead of the usual way to install dependencies
    pip_sync(venv, action)
    venv.pip_synced = True

    # Let tox know we've handled this case
    return True


@hookimpl
def tox_runenvreport(venv, action):  # pylint: disable=unused-argument
    """Get the installed packages and versions in this venv."""

    if venv.envconfig.config.tox_pip_sync.get("skip_listing", True):
        # This appears to be purely FYI, and just slows things down
        return ["*** listing modules disabled by tox-pip-sync in pyproject.toml ***"]

    return None


@hookimpl
def tox_runtest_pre(venv):
    """Perform arbitrary action after running tests for this venv."""

    # Note: None of this gets called for `.tox/.tox`, so we are using default
    # behavior for the venv tox installs itself into. On the other side, you
    # can't specify anything using versions, referring to files etc. for the
    # direct tox dependencies anyway: they are always plain unpinned
    # dependencies.

    if not getattr(venv, "pip_synced", False):
        # `tox_testenv_install_deps` does not get called every time we run tox
        # so assuming we've not run before, we should make sure we have
        tox_testenv_install_deps(venv=venv, action=venv.new_action("pip-sync"))
