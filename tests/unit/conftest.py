from unittest.mock import create_autospec

import pytest
from tox.action import Action
from tox.config import TestenvConfig as EnvConfig
from tox.venv import VirtualEnv


@pytest.fixture
def action():
    action = create_autospec(Action, instance=True)
    action.activity = "activity"

    return action


@pytest.fixture
def venv(tmpdir):
    # pytest has a real hard time creating autospecs for these as many of the
    # attributes are defined in '__init__' or added on later dynamically
    venv_model = VirtualEnv(
        envconfig=EnvConfig("env_name", config=None, factors=None, reader=None)
    )
    venv_model.envconfig.deps = []

    # We can't spec_set=True here, because it's totally normal to bold extra
    # things onto this as it runs in tox
    venv = create_autospec(venv_model, instance=True)
    venv._pcall.return_value = "Some command output"  # pylint: disable=protected-access
    venv.envconfig.envbindir = tmpdir / "bin"
    venv.path = tmpdir

    return venv
