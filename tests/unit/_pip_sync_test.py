from pathlib import Path

import pytest
from h_matchers import Any
from tox.config import DepConfig

from tox_pip_sync import pip_sync
from tox_pip_sync._pip_sync import pip_tools_run, requirements_files_for_env

# This test is heavily based on accessing underscored items
# pylint: disable=protected-access


class TestRequirementsFilesForEnv:
    def test_it_passes_through_requirements_files(self, requirements_files, venv):
        # tox smooshes together the -r and the filename for some reason
        venv.envconfig.deps = [DepConfig("-rreq_1.txt"), DepConfig("-creq_2.txt")]

        results = requirements_files()

        assert list(results) == ["req_1.txt"]

    @pytest.mark.parametrize(
        "dependency",
        (".", ".[tests]", "-e.", "package_name", "package<=5.0", "package==5.0"),
    )
    def test_it_compiles_normal_dependencies(
        self,
        requirements_files,
        requirements_set,
        venv,
        action,
        pip_tools_run,
        dependency,
    ):  # pylint: disable=too-many-arguments
        requirements_set.needs_compilation.return_value = True

        venv.envconfig.deps = [DepConfig(dependency)]

        file_names = requirements_files()

        unpinned = venv.path / "tox-pip-sync_0000.in"
        pip_tools_run.assert_called_once_with(
            "pip-compile",
            [str(unpinned)],
            message=Any.string(),
            venv=venv,
            action=action,
        )

        assert file_names[0] == str(venv.path / "tox-pip-sync_0000.txt")

    def test_it_writes_the_requirements_out_to_be_compiled(
        self, requirements_files, requirements_set, RequirementList, venv
    ):
        requirements_set.constrained_set.return_value = ["some_output", 0]
        venv.envconfig.deps = [DepConfig("-creqs.txt"), DepConfig(".[tests]")]

        requirements_files()

        RequirementList.from_strings.assert_called_once_with(
            Any.generator.containing(["-creqs.txt", ".[tests]"]).only()
        )
        requirements_set.constrained_set.assert_called_once_with(
            # This path is the difference between the venv dir and the project
            # root
            Path("../../")
        )
        unpinned = venv.path / "tox-pip-sync_0000.in"
        assert unpinned.read() == "some_output\n0"

    @pytest.mark.usefixtures("requirements_set")
    def test_it_re_uses_existing_files_when_compiling(
        self, requirements_files, venv, pip_tools_run
    ):
        venv.envconfig.deps = [DepConfig(".")]
        pinned_file = venv.path / "tox-pip-sync_0000.txt"
        pinned_file.write(".")

        file_names = requirements_files()

        assert file_names[0] == pinned_file
        pip_tools_run.assert_not_called()

    def test_it_cleans_up_old_files_when_compiling(self, requirements_files, venv):
        venv.envconfig.deps = [DepConfig(".")]
        old_pinned_file = venv.path / "tox-pip-sync_0000.txt"
        old_pinned_file.write(".")
        old_unpinned_file = venv.path / "tox-pip-sync_0000.in"
        old_unpinned_file.write(".")

        requirements_files()

        assert not old_pinned_file.exists()
        assert not old_unpinned_file.exists()

    def test_it_raises_if_pip_compile_fails_to_create_the_expected_file(
        self, venv, requirements_files, pip_tools_run
    ):
        pip_tools_run.side_effect = None
        venv.envconfig.deps = [DepConfig(".")]

        with pytest.raises(FileNotFoundError):
            requirements_files()

    @pytest.fixture
    def requirements_files(self, venv, action):
        def requirements_files():
            return list(requirements_files_for_env(venv, action))

        return requirements_files

    @pytest.fixture
    def requirements_set(self, RequirementList):
        requirements_set = RequirementList.from_strings.return_value
        requirements_set.hash.return_value = "0000"
        return requirements_set

    @pytest.fixture
    def RequirementList(self, patch):
        return patch("tox_pip_sync._pip_sync.RequirementList")

    @pytest.fixture(autouse=True)
    def pip_tools_run(self, patch):
        pip_tools_run = patch("tox_pip_sync._pip_sync.pip_tools_run")

        # Fake creating a file
        pip_tools_run.side_effect = (
            lambda exe_name, paths, message, venv, action: Path(paths[0])
            .with_suffix(".txt")
            .touch()
        )

        return pip_tools_run


class TestPipToolsRun:
    def test_it_calls_the_exe_through_tox(self, bin_dir, venv, action, exe_name):
        exe_file = bin_dir / exe_name
        exe_file.write_text("here", "utf-8")

        pip_tools_run(
            exe_name, ["arg_1", "arg_2"], message="A message", venv=venv, action=action
        )

        venv._pcall.assert_called_once_with(
            [str(exe_file), "arg_1", "arg_2"],
            cwd=venv.envconfig.config.toxinidir,
            action=action,
        )

        action.setactivity.assert_called_once_with(exe_name, "A message")

    def test_if_pip_sync_exe_is_missing_it_installs_it(
        self, bin_dir, venv, action, exe_name
    ):
        exe_file = bin_dir / exe_name
        venv._install.side_effect = lambda command, action: exe_file.write_text(
            "here", "utf-8"
        )

        pip_tools_run(exe_name, ["args"], message="any", venv=venv, action=action)

        venv._install.assert_called_once_with(["pip-tools", "--force"], action=action)

    def test_if_installing_pip_fails_we_raise(self, exe_name, venv, action):
        with pytest.raises(AssertionError):
            pip_tools_run(exe_name, ["args"], message="any", venv=venv, action=action)

    @pytest.fixture(params=("pip-sync", "pip-compile"))
    def exe_name(self, request):
        return request.param

    @pytest.fixture(autouse=True)
    def bin_dir(self, venv):
        return venv.envconfig.envbindir


class TestPipSync:
    def test_it(self, pip_tools_run, requirements_files_for_env, venv, action):
        # RequirementsFiles is a context manager
        requirements_files_for_env.return_value = ("requirements.txt",)

        pip_sync(venv, action)

        requirements_files_for_env.assert_called_once_with(venv, action)
        pip_tools_run.assert_called_once_with(
            "pip-sync", ["requirements.txt"], message=Any(), venv=venv, action=action
        )

    @pytest.fixture
    def pip_tools_run(self, patch):
        return patch("tox_pip_sync._pip_sync.pip_tools_run")

    @pytest.fixture
    def requirements_files_for_env(self, patch):
        return patch("tox_pip_sync._pip_sync.requirements_files_for_env")
