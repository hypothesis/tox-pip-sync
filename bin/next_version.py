"""Suggest a new tag to make a release with."""

from configparser import ConfigParser
from subprocess import check_output

from packaging import version


class VersionSuggester:
    """Detects various version indicators and suggests a nice next tag"""

    @classmethod
    def last_tag(cls):
        """Determine the last tag according to git."""

        tags = check_output(["git", "tag", "--list", "--sort=-v:refname"])
        if not tags:
            return None

        last_tag = tags.decode("utf-8").split("\n", 1)[0]
        return version.parse(last_tag)

    @classmethod
    def major_minor_version(cls):
        """Find the major minor declared in the setup.cfg."""

        config = ConfigParser()
        if not config.read("setup.cfg"):
            raise FileNotFoundError("setup.cfg")

        return version.parse(config["metadata"]["version"])

    @classmethod
    def suggest_tag(cls):
        """Suggest a new tag."""
        major_minor = cls.major_minor_version()

        last_tag = cls.last_tag()
        if last_tag is None:
            build = 0
        elif last_tag.release[:2] == major_minor.release[:2]:
            build = last_tag.release[2] + 1
        elif last_tag > major_minor:
            raise ValueError(
                f"The last tag 'v{last_tag}' is ahead of the declared version '{major_minor}'"
            )
        else:
            build = 0

        return f"v{major_minor}.{build}"


if __name__ == "__main__":  # pragma: no cover
    print(VersionSuggester.suggest_tag())
