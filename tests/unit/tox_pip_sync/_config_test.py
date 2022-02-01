import pytest

from tox_pip_sync import load_config


class TestLoadConfig:
    @pytest.mark.parametrize(
        "file_name,content,expected_values",
        (
            (
                "pyproject.toml",
                "[tool.tox.tox_pip_sync]\na_setting = true",
                {"a_setting": True},
            ),
            ("tox.ini", "[tox_pip_sync]\na_setting = true", {"a_setting": "true"}),
        ),
    )
    def test_it_can_read_from_a_file(self, tmpdir, file_name, content, expected_values):
        config_file = tmpdir / file_name
        config_file.write_text(content, encoding="utf-8")

        settings = load_config(tmpdir)

        assert settings == expected_values

    @pytest.mark.parametrize("file_name", ("pyproject.toml", "tox.ini"))
    def test_it_can_handle_the_section_being_missing(self, tmpdir, file_name):
        project_file = tmpdir / file_name
        project_file.write_text("", encoding="utf-8")

        settings = load_config(tmpdir)

        assert not settings

    def test_it_can_handle_the_files_being_missing(self, tmpdir):
        settings = load_config(tmpdir)

        assert not settings

    @pytest.mark.parametrize(
        "option,value,expected",
        (
            ("skip_listing", "1", True),
            ("skip_listing", "0", False),
            ("skip_listing", "true", True),
            ("skip_listing", "false", False),
            ("skip_listing", "on", True),
            ("skip_listing", "off", False),
            ("skip_listing", "True", True),
            # Note this isn't part of what ConfigParser considers falsy
            ("skip_listing", "False", True),
        ),
    )
    def test_it_coerces_values_for_ini_files(self, tmpdir, option, value, expected):
        tox_ini = tmpdir / "tox.ini"
        tox_ini.write_text(f"[tox_pip_sync]\n{option} = {value}", encoding="utf-8")

        settings = load_config(tmpdir)

        assert settings == {option: expected}
