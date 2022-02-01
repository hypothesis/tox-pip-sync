import json
from pathlib import Path
from unittest.mock import call, sentinel

import pytest
from h_matchers import Any
from tox.config import DepConfig

from tox_pip_sync import pip_sync
from tox_pip_sync._pip_sync import EnvData, pip_tools_run, requirements_files_for_env
from tox_pip_sync._requirements import PipRequirement

# This test is heavily based on accessing underscored items
# pylint: disable=protected-access


class TestRequirementsFilesForEnv:
    def test_it_passes_through_requirements_files(
        self, requirements_files, requirements_list
    ):
        # tox smooshes together the -r and the filename for some reason
        requirements_list.needs_compilation = False
        requirements_list.__iter__.return_value = [
            PipRequirement("-rreq_1.txt"),
            PipRequirement("-creq_2.txt"),
        ]

        results = requirements_files()

        assert list(results) == ["req_1.txt"]

    @pytest.mark.parametrize(
        "dependency",
        (".", ".[tests]", "-e.", "package_name", "package<=5.0", "package==5.0"),
    )
    def test_it_compiles_normal_dependencies(
        self,
        requirements_files,
        requirements_list,
        venv,
        action,
        pip_tools_run,
        dependency,
    ):  # pylint: disable=too-many-arguments
        requirements_list.needs_compilation.return_value = True
        requirements_list.__iter__.return_value = [PipRequirement(dependency)]

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
        self, requirements_files, requirements_list, venv
    ):
        requirements_list.needs_compilation.return_value = True
        requirements_list.constrained_set.return_value = ["some_output", 0]
        requirements_list.__iter__.return_value = [
            PipRequirement("-creqs.txt"),
            PipRequirement(".[tests]"),
        ]

        requirements_files()

        requirements_list.constrained_set.assert_called_once_with(
            # This path is the difference between the venv dir and the project
            # root
            Path("../../")
        )
        unpinned = venv.path / "tox-pip-sync_0000.in"
        assert unpinned.read() == "some_output\n0"

    @pytest.mark.usefixtures("requirements_list")
    def test_it_re_uses_existing_files_when_compiling(
        self, requirements_files, venv, pip_tools_run, requirements_list
    ):
        requirements_list.__iter__.return_value = [PipRequirement(".")]
        pinned_file = venv.path / "tox-pip-sync_0000.txt"
        pinned_file.write(".")

        file_names = requirements_files()

        assert file_names[0] == pinned_file
        pip_tools_run.assert_not_called()

    def test_it_cleans_up_old_files_when_compiling(
        self, requirements_files, venv, requirements_list
    ):
        requirements_list.__iter__.return_value = [PipRequirement(".")]
        requirements_list.hash.return_value = "0000"
        old_pinned_file = venv.path / "tox-pip-sync_1111.txt"
        old_pinned_file.write(".")
        old_unpinned_file = venv.path / "tox-pip-sync_1111.in"
        old_unpinned_file.write(".")

        requirements_files()

        assert not old_pinned_file.exists()
        assert not old_unpinned_file.exists()

    def test_it_raises_if_pip_compile_fails_to_create_the_expected_file(
        self, requirements_files, pip_tools_run, requirements_list
    ):
        pip_tools_run.side_effect = None
        requirements_list.__iter__.return_value = [PipRequirement(".")]

        with pytest.raises(FileNotFoundError):
            requirements_files()

    @pytest.fixture
    def requirements_files(self, venv, action, requirements_list):
        def requirements_files():
            return list(requirements_files_for_env(venv, action, requirements_list))

        return requirements_files

    @pytest.fixture
    def requirements_list(self, patch):
        RequirementList = patch("tox_pip_sync._pip_sync.RequirementList")
        requirements_list = RequirementList.from_strings.return_value
        requirements_list.hash.return_value = "0000"
        return requirements_list

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

        venv._install.assert_has_calls(
            [
                call(["pip-tools", "--force"], action=action),
                call(["pip<22", "--force"], action=action),
            ]
        )

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
    def test_it(
        self, pip_tools_run, requirements_files_for_env, venv, action, RequirementList
    ):  # pylint: disable=too-many-arguments
        requirements_files_for_env.return_value = ("requirements.txt",)
        venv.envconfig.deps = [DepConfig("package_name")]

        pip_sync(venv, action, skip_on_hash_match=False)

        RequirementList.from_strings.assert_called_once_with(
            Any.generator.containing(["package_name"])
        )
        requirements_files_for_env.assert_called_once_with(
            venv, action, RequirementList.from_strings.return_value
        )
        pip_tools_run.assert_called_once_with(
            "pip-sync", ["requirements.txt"], message=Any(), venv=venv, action=action
        )

    def test_it_skips_if_hashes_match(
        self, venv, action, RequirementList, EnvData, pip_tools_run
    ):  # pylint: disable=too-many-arguments
        requirements = RequirementList.from_strings.return_value
        requirements.hash.return_value = sentinel.matching_hash_value
        EnvData.return_value.last_hash = sentinel.matching_hash_value

        pip_sync(venv, action, skip_on_hash_match=True)

        pip_tools_run.assert_not_called()

    def test_it_runs_if_hashes_differ(
        self, venv, action, RequirementList, EnvData, pip_tools_run
    ):  # pylint: disable=too-many-arguments
        requirements = RequirementList.from_strings.return_value
        requirements.hash.return_value = sentinel.hash_value_1
        EnvData.return_value.last_hash = sentinel.hash_value_2

        pip_sync(venv, action, skip_on_hash_match=True)

        pip_tools_run.assert_called_once()

    @pytest.mark.usefixtures("pip_tools_run")
    def test_it_saves_the_hash(self, venv, action, RequirementList, EnvData):
        pip_sync(venv, action, skip_on_hash_match=True)

        requirements = RequirementList.from_strings.return_value
        requirements.hash.assert_called_once_with(
            root_dir=venv.envconfig.config.setupdir
        )

        EnvData.assert_called_once_with(venv.path)
        EnvData.return_value.save.assert_called_once_with(
            requirements_hash=requirements.hash.return_value
        )

    @pytest.fixture(autouse=True)
    def pip_tools_run(self, patch):
        return patch("tox_pip_sync._pip_sync.pip_tools_run")

    @pytest.fixture(autouse=True)
    def requirements_files_for_env(self, patch):
        return patch("tox_pip_sync._pip_sync.requirements_files_for_env")

    @pytest.fixture(autouse=True)
    def RequirementList(self, patch):
        return patch("tox_pip_sync._pip_sync.RequirementList")

    @pytest.fixture(autouse=True)
    def EnvData(self, patch):
        return patch("tox_pip_sync._pip_sync.EnvData")


class TestEnvData:
    def test_it_can_load_the_hash(self, tmpdir):
        (tmpdir / "tox-pip-sync.json").write_text(
            json.dumps({"hash": "value"}), "utf-8"
        )
        last_hash = EnvData(tmpdir).last_hash

        assert last_hash == "value"

    def test_it_fails_gracefully_if_the_file_is_missing(self, tmpdir):
        last_hash = EnvData(tmpdir).last_hash

        assert last_hash is None

    def test_it_can_save_the_hash(self, tmpdir):
        EnvData(tmpdir).save(requirements_hash="value")

        content = json.loads((tmpdir / "tox-pip-sync.json").read_text("utf-8"))
        assert content == {"hash": "value"}
