import os

import pytest
from h_matchers import Any
from tox.config import DepConfig

from tox_pip_sync import pip_sync

# This test is heavily based on accessing underscored items
# pylint: disable=protected-access


class TestPipSync:
    def test_it_passes_through_requirements_files(self, venv, action, pip_sync_exe):
        # tox smooshes together the -r and the filename for some reason
        venv.envconfig.deps = [DepConfig("-rreq_1.txt"), DepConfig("-rreq_2.txt")]

        pip_sync(venv, action)

        venv._pcall.assert_called_once_with(
            [pip_sync_exe, "req_1.txt", "req_2.txt"],
            cwd=venv.envconfig.config.toxinidir,
            action=action,
        )

        action.setactivity.assert_called_once_with(
            "pip-sync", Any.string.containing(venv._pcall.return_value)
        )

    def test_it_creates_a_new_requirements_file_for_named_deps(
        self, venv, action, pip_sync_exe
    ):
        venv.envconfig.deps = [DepConfig("package_1"), DepConfig("package_2")]

        def _pcall(command, cwd=None, action=None):  # pylint: disable=unused-argument
            # We have to capture this file content now, as the file is deleted
            _pcall.file_name = command[1]
            with open(_pcall.file_name) as handle:
                _pcall.file_content = handle.read()

            return "String command return"

        venv._pcall.side_effect = _pcall

        pip_sync(venv, action)

        assert _pcall.file_content == "package_1\npackage_2\n"
        assert not os.path.exists(_pcall.file_name)  # We clean up after ourselves
        venv._pcall.assert_called_once_with(
            [pip_sync_exe, Any.string()],
            cwd=venv.envconfig.config.toxinidir,
            action=action,
        )

    def test_if_pip_sync_exe_is_missing_it_installs_it(
        self, venv, action, pip_sync_exe
    ):
        os.unlink(pip_sync_exe)
        venv._install.side_effect = lambda command, action: pip_sync_exe.write_text(
            "here", "utf-8"
        )

        pip_sync(venv, action)

        venv._install.assert_called_once_with(["pip-tools", "--force"], action=action)

    def test_if_installing_pip_fails_we_raise(self, venv, action, pip_sync_exe):
        os.unlink(pip_sync_exe)

        with pytest.raises(FileNotFoundError):
            pip_sync(venv, action)

    @pytest.fixture(autouse=True)
    def pip_sync_exe(self, tmpdir):
        bin_dir = tmpdir / "bin"
        bin_dir.mkdir()

        pip_sync_exe = bin_dir / "pip-sync"
        pip_sync_exe.write_text("pip-sync-exe", "utf-8")

        return pip_sync_exe
