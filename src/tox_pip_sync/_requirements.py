from copy import deepcopy
from enum import Enum
from functools import lru_cache
from hashlib import md5


class RequirementList(list):
    PROJECT_FILE_SOURCES = ("setup.py", "setup.cfg", "pyproject.toml")

    @classmethod
    def from_strings(cls, strings):
        return cls([PipRequirement(req) for req in strings])

    @classmethod
    def from_requirements_file(cls, filename):
        requirements = cls()

        with open(filename) as handle:
            for line in handle:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue

                if "#" in line:
                    line = line[: line.index("#")]

                requirements.append(PipRequirement(line))

        return requirements

    @property
    def needs_compilation(self):
        """Find out if there is anything to compile here."""

        # We aren't doing anything very in depth here, we just assume that
        # anything which isn't a reference to a file has not been compiled and
        # anything which is has been run through `pip-compile` by the user
        return any(not req.filename for req in self)

    def constrained_set(self, relative_root):
        """Convert all -r requirements to constraints instead."""

        requirements = RequirementList()

        for req in self:
            if req.filename:
                req = deepcopy(req)

                # When pip-compile finds a reference like -c it assumes it's
                # relative to the current path, so we need to offset back
                # to the root. Oddly it doesn't do this for -e, that is
                # relative to the current working directory.
                req.filename = relative_root.joinpath(req.filename)

                if req.arg_type == PipRequirement.ArgType.REFERENCE:
                    req.arg_type = PipRequirement.ArgType.CONSTRAINT

            requirements.append(req)

        return requirements

    @lru_cache(1)
    def hash(self, root_dir):
        """Get a hash of this set of requirements.

        This should change if any relevant change to files is detected.

        :param root_dir: The root of the project to resolve project files and
            requirements includes against as `pathlib.Path` object
        :return: An hex string digest of the requirements
        """
        digest = md5()
        for fragment in self._hash_fragments(root_dir):
            digest.update(str(fragment).encode("utf-8"))

        return digest.hexdigest()

    def _hash_fragments(self, root_dir):
        """Yield fragments for hashing from this set."""
        for req in self:
            yield req

            if req.filename:
                # pylint: disable=protected-access
                # This is an instance of this class, making this fine...

                filename = req.filename
                # If this is a relative path, make it relative to the root
                if not filename.startswith("/"):
                    filename = root_dir / req.filename

                yield from self.from_requirements_file(filename)._hash_fragments(
                    root_dir
                )

            if req.is_local:
                yield from self._hash_fragments_for_project(root_dir)

    def _hash_fragments_for_project(self, root_dir):
        """Yield fragments for project files."""

        # We can't be sure exactly what's required without doing some horrible
        # parsing, but what we can say is, if the contents of some of these
        # files have changed, there _might_ be a possibility that the env needs
        # to be rebuilt.

        for file_name in self.PROJECT_FILE_SOURCES:
            project_file = root_dir / file_name
            if project_file.exists():
                # Use the whole contents
                yield project_file.read()

    def __hash__(self):
        # Ensure we are hashable, and also ensure that different instances of
        # this class hash to different things, even if they have the same
        # contents. Otherwise the `@lru_cache` above ends up being shared
        # between all instances
        return hash(id(self))


class PipRequirement:
    """A pip compatible requirement."""

    class ArgType(Enum):
        """The type of argument used with this argument."""

        NONE = None
        CONSTRAINT = "-c"
        EDITABLE = "-e"
        REFERENCE = "-r"

    arg_type = ArgType.NONE
    requirement = None
    filename = None

    def __init__(self, string):
        """Initialise a requirement from a raw string."""

        string = string.strip()

        if string.startswith("-"):
            self.arg_type = self.ArgType(string[:2])

            string = string[2:].strip()

            if self.arg_type in (self.ArgType.REFERENCE, self.ArgType.CONSTRAINT):
                self.filename = string
                return

        self.requirement = string

    @property
    def is_local(self):
        """Get whether the dependency points to the local directory."""

        return bool(self.requirement and self.requirement.startswith("."))

    def __str__(self):
        result = ""
        if self.arg_type != self.ArgType.NONE:
            result = self.arg_type.value + " "

            if self.filename:
                return result + str(self.filename)

        return result + self.requirement

    def __eq__(self, other):
        if not isinstance(other, PipRequirement):
            return False

        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def _key(self):
        return self.arg_type, self.requirement, str(self.filename)

    def __repr__(self):
        return f"PipRequirement('{self.__str__()}')"
