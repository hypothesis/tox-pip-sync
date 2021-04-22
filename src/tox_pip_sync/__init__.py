import pluggy

from tox_pip_sync._pip_sync import pip_sync

hookimpl = pluggy.HookimplMarker("tox")


@hookimpl
def tox_testenv_create(venv, action):  # pylint: disable=unused-argument
    """Perform creation action for this venv."""

    if action.activity == "recreate":
        # By default tox completely destroys and recreates a virtual env when
        # it notices changes. It is currently capable of noticing changes in
        # deps directly listed in the tox.ini file. In version 4 it may also
        # become "-r requirements.txt" aware too. pip-sync can however remove
        # the dependencies that aren't needed and is equivalent to a recreate
        # without starting completely from scratch

        # Let tox know we're handling this and not to run default behavior
        action.setactivity("pip-sync", "Skipping virtual env recreation")
        return True

    # Let tox know we _don't_ want to handle this case
    return None


@hookimpl
def tox_testenv_install_deps(venv, action):
    """Perform install dependencies action for this venv."""

    # Call our pip sync method instead of the usual way to install dependencies
    pip_sync(venv, action)
    venv.pip_synced = True

    # Let tox know we've handled this case
    return True


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
