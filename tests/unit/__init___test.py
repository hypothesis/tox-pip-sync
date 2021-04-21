import pytest

from tox_pip_sync import tox_runtest_pre, tox_testenv_create, tox_testenv_install_deps


class TestToxTestenvCreate:
    def test_it_does_nothing_for_creates(self, venv, action):
        action.activity = "create"

        result = tox_testenv_create(venv, action)

        # We don't want to interfere
        assert not result

    def test_it_disables_recreates(self, venv, action):
        action.activity = "recreate"

        result = tox_testenv_create(venv, action)

        # We want to take control and prevent tox default behavior
        assert result


class TestToxTestenvInstallDeps:
    def test_it(self, venv, action, pip_sync):
        result = tox_testenv_install_deps(venv, action)

        pip_sync.assert_called_once_with(venv, action)

        assert venv.pip_synced
        assert result

    @pytest.fixture(autouse=True)
    def pip_sync(self, patch):
        return patch("tox_pip_sync.pip_sync")


class TestToxRuntestPre:
    def test_it_installs_deps_if_not_already_done(self, venv, tox_testenv_install_deps):
        tox_runtest_pre(venv)

        tox_testenv_install_deps.assert_called_once_with(
            venv=venv, action=venv.new_action.return_value
        )
        venv.new_action.assert_called_once_with("pip-sync")

    def test_it_does_nothing_if_venv_already_synced(
        self, venv, tox_testenv_install_deps
    ):
        venv.pip_synced = True

        tox_runtest_pre(venv)

        tox_testenv_install_deps.assert_not_called()

    @pytest.fixture(autouse=True)
    def tox_testenv_install_deps(self, patch):
        return patch("tox_pip_sync.tox_testenv_install_deps")
