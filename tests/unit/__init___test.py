from unittest.mock import create_autospec, sentinel

import pytest
from h_matchers import Any
from tox.config import Config

from tox_pip_sync import (
    tox_configure,
    tox_runenvreport,
    tox_runtest_pre,
    tox_testenv_create,
    tox_testenv_install_deps,
)


class TestToxConfigure:
    def test_it_sets_the_config(self, load_config, config):
        tox_configure(config)

        load_config.assert_called_once_with(config.setupdir)
        assert config.tox_pip_sync == load_config.return_value

    @pytest.fixture
    def load_config(self, patch):
        return patch("tox_pip_sync.load_config")

    @pytest.fixture
    def config(self):
        config = create_autospec(Config)
        config.setupdir = sentinel.setupdir
        return config


class TestRunenvreport:
    @pytest.mark.parametrize(
        "skip_listing,expected", ((True, Any.list.of_size(at_least=1)), (False, None))
    )
    def test_it(self, skip_listing, expected, venv, action):
        venv.envconfig.config.tox_pip_sync = {"skip_listing": skip_listing}

        result = tox_runenvreport(venv, action)

        assert result == expected


class TestToxTestenvCreate:
    def test_it_clears_old_files(self, venv, action, clear_compiled_files):
        action.activity = "create"

        result = tox_testenv_create(venv, action)

        clear_compiled_files.assert_called_once_with(venv)
        # We don't want to interfere
        assert not result

    @pytest.fixture(autouse=True)
    def clear_compiled_files(self, patch):
        return patch("tox_pip_sync.clear_compiled_files")


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
