import pytest
from h_matchers import Any

from tox_pip_sync._requirements import PipRequirement, RequirementList


class TestRequirementsList:
    def test_from_strings(self):
        req_set = RequirementList.from_strings(["package_1", "package_2"])

        assert (
            req_set
            == Any.list.of_type(RequirementList)
            .containing([PipRequirement("package_1"), PipRequirement("package_2")])
            .only()
        )

    @pytest.mark.parametrize(
        "line,requirements",
        (
            ("# comment", []),
            ("     ", []),
            ("", []),
            ("   package ", [PipRequirement("package")]),
            ("package # comment", [PipRequirement("package")]),
            ("-r requirements.txt", [PipRequirement("-r requirements.txt")]),
            ("-rrequirements.txt", [PipRequirement("-r requirements.txt")]),
            ("-c requirements.txt", [PipRequirement("-c requirements.txt")]),
            ("-crequirements.txt", [PipRequirement("-c requirements.txt")]),
            ("-e .", [PipRequirement("-e .")]),
            ("-e.", [PipRequirement("-e .")]),
        ),
    )
    def test_from_requirements_file(self, line, requirements, tmpdir):
        req_file = tmpdir / "requirements.txt"
        req_file.write_text(line, encoding="utf-8")

        req_set = RequirementList.from_requirements_file(req_file)

        assert req_set == requirements

    @pytest.mark.parametrize(
        "requirement,needs_compilation",
        (
            (PipRequirement("-r requirements.txt"), False),
            (PipRequirement("-c requirements.txt"), False),
            (PipRequirement("."), True),
            (PipRequirement(".[tests]"), True),
            (PipRequirement("-e .[tests]"), True),
            (PipRequirement("package"), True),
            (PipRequirement("package<=5.0"), True),
            # For the moment any plain dependency will trigger this, even if pinned
            (PipRequirement("package==1.2.3"), True),
        ),
    )
    def test_needs_compilation(self, requirement, needs_compilation):
        req_set = RequirementList([requirement])

        assert req_set.needs_compilation == needs_compilation

    def test_constrained_set(self):
        req_set = RequirementList.from_strings(
            ["-r requirements.txt", "-c constrained.txt", "-e editable", "package"]
        )

        assert req_set.constrained_set() == RequirementList.from_strings(
            [
                "-c requirements.txt",  # <<< The change is the -c here
                "-c constrained.txt",
                "-e editable",
                "package",
            ]
        )


class TestRequirementsSetHashing:
    def test_hash_is_repeatable(self, get_hash):
        assert get_hash() == get_hash()

    @pytest.mark.parametrize("file_name", ("setup.py", "setup.cfg", "pyproject.toml"))
    def test_it_detects_changes_to_project_files(
        self, get_hash, project_dir, file_name
    ):
        first_hash = get_hash()

        project_file = project_dir / file_name
        project_file.write_text("any change", encoding="utf-8")

        assert get_hash() != first_hash

    @pytest.mark.parametrize("file_name", ("setup.py", "setup.cfg", "pyproject.toml"))
    def test_it_is_happy_with_project_files_being_missing(
        self, get_hash, project_dir, file_name
    ):
        project_file = project_dir / file_name
        project_file.remove()

        assert get_hash()

    @pytest.mark.parametrize("file_name", ("requirements.txt", "child-reqs.txt"))
    def test_it_detects_changes_to_requirements_files(
        self, get_hash, project_dir, file_name
    ):
        # This is a little different, as the actual contents matter, and the
        # fact that the files are referrred from each other. We check that we
        # spot changes in the file we reference, and the one that references
        first_hash = get_hash()

        requirements_file = project_dir / file_name
        requirements_file.write_text("a_new_dependency==1.0.2", encoding="utf-8")

        assert get_hash() != first_hash

    def test_it_detects_changes_to_requirements_in_tox(self, get_hash, project_reqs):
        first_hash = get_hash()

        project_reqs.append("a_new_package")

        assert get_hash() != first_hash

    @pytest.fixture
    def get_hash(self, project_reqs, project_dir):
        def get_hash():
            return RequirementList.from_strings(project_reqs).hash(project_dir)

        return get_hash

    @pytest.fixture
    def project_reqs(self, project_dir):  # pylint: disable=unused-argument
        return ["-r child-reqs.txt", ".", "package_3==2.2.2"]

    @pytest.fixture
    def project_dir(self, tmpdir):
        for name in ("setup.py", "setup.cfg", "pyproject.toml"):
            project_file = tmpdir / name
            project_file.write_text(f"Content: {name}", encoding="utf-8")

        reqs = tmpdir / "requirements.txt"
        reqs.write_text("package==1.1.1", encoding="utf-8")

        reqs = tmpdir / "child-reqs.txt"
        reqs.write_text("-r requirements.txt\npackage_2=2.2.2", encoding="utf-8")

        return tmpdir


class TestPipRequirement:
    @pytest.mark.parametrize(
        "string,attrs",
        (
            (
                "package",
                {
                    "arg_type": PipRequirement.ArgType.NONE,
                    "filename": None,
                    "requirement": "package",
                },
            ),
            ("package==12.0", {"requirement": "package==12.0"}),
            ("   package  ", {"requirement": "package"}),
            (
                "-r requirements.txt",
                {
                    "arg_type": PipRequirement.ArgType.REFERENCE,
                    "filename": "requirements.txt",
                    "requirement": None,
                },
            ),
            (
                "-rrequirements.txt",
                {
                    "filename": "requirements.txt",
                },
            ),
            (
                "-c requirements.txt",
                {
                    "arg_type": PipRequirement.ArgType.CONSTRAINT,
                    "filename": "requirements.txt",
                    "requirement": None,
                },
            ),
            (
                "-crequirements.txt",
                {
                    "filename": "requirements.txt",
                },
            ),
            (
                "-e package",
                {
                    "arg_type": PipRequirement.ArgType.EDITABLE,
                    "filename": None,
                    "requirement": "package",
                },
            ),
            ("-epackage", {"requirement": "package"}),
        ),
    )
    def test_it_parses(self, string, attrs):
        req = PipRequirement(string)

        assert Any.instance_of(PipRequirement).with_attrs(attrs) == req

    @pytest.mark.parametrize(
        "string,is_local",
        (
            (".", True),
            (".[tests]", True),
            ("-e .[tests]", True),
            ("package", False),
            ("-r requirements.txt", False),
            # ("-r .", True),  # not sure if this is valid or not?
        ),
    )
    def test_is_local(self, string, is_local):
        req = PipRequirement(string)

        assert bool(req.is_local) == is_local

    def test_equality(self):
        req = PipRequirement("-e package")

        assert req == PipRequirement("-e package")
        assert req != PipRequirement("package")
        assert req != "-e package"

    def test_it_can_hash(self):
        assert hash(PipRequirement("package")) == hash(PipRequirement("package"))

    @pytest.mark.parametrize(
        "string", ("package==1.2.3", "-r requirements.txt", "-e .")
    )
    def test_repr(self, string):
        output = repr(PipRequirement(string))

        assert "PipRequirement" in output
        assert string in output
