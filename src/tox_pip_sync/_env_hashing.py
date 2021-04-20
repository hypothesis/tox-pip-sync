import json
import os
from functools import lru_cache
from hashlib import md5


class VirtualEnvDigest:
    # The location to store our digest file inside the virtual env
    DIGEST_FILE = ".tox-pip-sync.json"

    # Places where dependencies _might_ have been declared
    PROJECT_FILE_SOURCES = ("setup.py", "setup.cfg", "pyproject.toml")

    # Sub directories for virtual envs to include in hashing
    VENV_DIRS = ("bin", "lib", "share", "include")

    def __init__(self, venv, hash_venv=True):
        self.venv = venv
        self.hash_venv = hash_venv

        self._digest_file = venv.envconfig.envdir / self.DIGEST_FILE

    def save(self):
        self._digest_file.write_text(
            json.dumps({"hash": self.digest}), encoding="utf-8"
        )

    @property
    def in_sync(self):
        digest_on_disk = self.digest_on_disk
        if not digest_on_disk:
            return False

        return self.digest == digest_on_disk

    @property
    def digest_on_disk(self):
        if self._digest_file.exists():
            data = json.loads(self._digest_file.read_text(encoding="utf-8"))
            return data["hash"]

        return None

    @property
    @lru_cache(1)
    def digest(self):
        digest = md5()

        for fragment in self._from_dependency_strings(
            [dep.name for dep in self.venv.envconfig.deps]
        ):
            digest.update(fragment.encode("utf-8"))

        if self.hash_venv:
            for fragment in self._from_venv():
                digest.update(fragment.encode("utf-8"))

        return digest.hexdigest()

    def _from_venv(self):
        files = []

        for root_dir in self.VENV_DIRS:
            for path, _, file_names in os.walk(self.venv.envconfig.envdir / root_dir):
                files.extend(os.path.join(path, file_name) for file_name in file_names)

        for file_name in sorted(files):
            if file_name.endswith(".pyc"):
                continue

            yield self._file_fragment(file_name)

    @classmethod
    def _file_fragment(cls, file_name):
        stats = os.stat(file_name)
        return f"{file_name}/{stats.st_size}/{stats.st_mtime}"

    def _from_dependency_strings(self, deps):
        for dep in deps:
            yield dep

            if dep.startswith("-r") or dep.startswith("-c"):
                yield from self._from_requirements_file(dep[2:])

            elif dep.startswith("-e"):
                editable = dep[2:]
                if editable.startswith("."):
                    yield from self._from_project()

            elif dep.startswith("."):
                # This is a dependency like '.[tests]'
                yield from self._from_project()

    def _from_requirements_file(self, requirements_file):
        requirements_file = self.venv.envconfig.changedir / requirements_file

        with open(requirements_file) as handle:
            for line in handle:
                if "#" in line:
                    line = line[: line.index("#")]

                line = line.strip()
                if not line:
                    continue

                yield from self._from_dependency_strings([line])

    def _from_project(self):
        # We can't be sure exactly what's required without doing some horrible
        # parsing, but what we can say is, if the contents of some of these
        # files have changed, there _might_ be a possibility that the env needs
        # to be rebuilt.

        project_dir = self.venv.envconfig.changedir

        for file_name in self.PROJECT_FILE_SOURCES:
            project_file = project_dir / file_name
            if project_file.exists():
                yield self._file_fragment(project_file)
