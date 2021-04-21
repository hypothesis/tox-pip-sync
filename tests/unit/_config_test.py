from tox_pip_sync import load_config


class TestLoadConfig:
    def test_it_can_read_the_project_file(self, tmpdir):
        project_file = tmpdir / "pyproject.toml"
        project_file.write_text(
            "[tool.tox.tox_pip_sync]\na_setting = true", encoding="utf-8"
        )

        settings = load_config(tmpdir)

        assert settings == {"a_setting": True}

    def test_it_can_handle_the_section_being_missing(self, tmpdir):
        project_file = tmpdir / "pyproject.toml"
        project_file.write_text("", encoding="utf-8")

        settings = load_config(tmpdir)

        assert settings == {}

    def test_it_can_handle_the_file_being_missing(self, tmpdir):
        settings = load_config(tmpdir)

        assert settings == {}
