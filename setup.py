import os
from configparser import ConfigParser

from setuptools import find_packages, setup


class Package:
    def __init__(self, config):
        metadata = config["metadata"]
        options = config["options"]

        self.options = options
        self.name = metadata["name"]
        self.version = metadata["version"]

    def tests_require(self):
        return self.options["tests_require"] + self.options["install_requires"]

    def read_egg_version(self):
        pkg_info_file = None
        # PKG-INFO can be in different places depending on whether we are a
        # source distribution or a checked out copy etc.
        for location in [
            "PKG-INFO",
            "src/" + self.name + ".egg-info/PKG-INFO",
            self.name + ".egg-info/PKG-INFO",
        ]:
            if os.path.isfile(location):
                pkg_info_file = location

        if not pkg_info_file:
            return None

        with open(pkg_info_file) as fh:
            for line in fh:
                if line.startswith("Version"):
                    return line.strip().split("Version: ")[-1]

    def get_version(self, build_var="BUILD"):
        """Gets a version reading from the specified environment variable

        This expects the variable to contain something like:

         * refs/heads/<branch_name> - This will be ignored
         * refs/tags/v<version> - This will be used if it matches our major
                                  minor number
         * v<version> - This will be used if it matches our major minor number

        If this is not present then we will read from the .egg-info/ data if
        possible.

        Finally a fallback development version is provided.

        :param build_var: The enviroment to
        :return: A version string
        """
        # If we have a build argument we should honour it if we can
        build = os.environ.get(build_var)
        if build:
            if build.startswith("refs/heads/"):
                # We are being built via CI from a branch: we'll return a
                # dummy value marking this as an 'alpha' release
                return self.version + ".a0"

            if build.startswith("refs/tags/"):
                # We are being built via CI from a tag: strip the refs stuff
                build = build.replace("refs/tags/", "")

            start = "v" + self.version + "."
            if not build.startswith(start):
                raise ValueError(
                    'Expected build to be "{}*", got "{}"'.format(start, build)
                )

            return self.version + "." + build[len(start) :]

        # If not, we should try and read it from the .egg-info/ data

        # We need to do this for source distributions, as setup.py is re-run
        # when installed this way, and we would always get 'dev0' as the
        # version wheels and binary installs don't work this way and read
        # from PKG-INFO for them selves
        egg_version = self.read_egg_version()
        if egg_version:
            return egg_version

        # Otherwise create a 'dev' build which will be counted by pip as
        # 'later' than the major version no matter what
        return self.version + ".dev0"


config = ConfigParser()
config.read("setup.cfg")
package = Package(config)

setup(
    # Metadata
    # https://docs.python.org/3/distutils/setupscript.html#additional-meta-data
    version=package.get_version(),
    # Contents and dependencies
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    # Read the MANIFEST.in
    include_package_data=True,
    # Add support for pip install .[tests]
    extras_require={"tests": package.tests_require()},
    tests_require=package.tests_require(),
)
