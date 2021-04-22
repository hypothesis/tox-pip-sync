# tox-pip-sync

Manage virtualenvs automatically with `pip-sync`.

Usage
-----

In `tox.ini` add:

```ini
[tox]
requires =
  tox-pip-sync

deps =
    tests: -r pinned-requirements.txt
    tests: -e .
    tests: ad-hoc-requirement
```

This will cause `pip-sync` from [`pip-tools`](https://pypi.org/project/pip-tools/)
to be used to synchronise virtual envs with the requirements specified in the
`tox.ini` on every run.

This means never having to run `--recreate` and should be significantly faster
than plain `tox` when re-using existing virtual envs.

### How `tox-pip-sync` handles dependencies

`tox-pip-sync` expects any requirements to be either:

 * Specified directly in the `tox.ini`
 * Stored in a **pinned** requirements file referenced from `tox.ini` with `-r` _(best!)_

Pinned dependencies are the best and fastest way to specify your dependencies
and the easiest way to ensure compatibility is to use a file created by
`pip-compile` as `-r requirements.txt`. See the
[`pip-tools`](https://pypi.org/project/pip-tools/) docs for more info.

__Warning: Using unpinned requirements in external files will cause problems!__

We can also track requirements specified in the `tox.ini` file like this:

 * `.[tests]`
 * `-e .`
 * `ad-hoc`
 * `ad-hoc<=5.0`
 * `ad-hoc==5.0`

For any dependency specified directly in the `tox.ini` (not using `-r`) we will:

 * Create an unpinned requirements file in the virtual env directory
 * Constrain it (using `-c`) if there are any externally referenced dependency
   files using `-r`
 * Compile it
 * Use the compiled version along side those specified with `-r`

For references like `-c` and `-r` we will recursively check the specified
files for changes. For local references like `.` or `-e .[tests]` we will check
the following files for changes:

 * `pyproject.toml`
 * `setup.cfg`
 * `setup.py`

If any changes are detected we will recompile the dependencies. This means any
updates you make should be reflected, but if you have unpinned dependencies
which are met in your virtual environment, they will not be updated and could
get out of date.

### Things which can break `tox-pip-sync`

 * Referencing requirements files with unpinned requirements (use `pip-compile`
   first)
 * Doing something fancy in `setup.py` to read the requirements from another
   location

Hacking
-------

### Installing tox-pip-sync in a development environment

#### You will need

* [Git](https://git-scm.com/)

* [pyenv](https://github.com/pyenv/pyenv)
  Follow the instructions in the pyenv README to install it.
  The Homebrew method works best on macOS.
  On Ubuntu follow the Basic GitHub Checkout method.

#### Clone the git repo

```terminal
git clone https://github.com/hypothesis/tox-pip-sync.git
```

This will download the code into a `tox-pip-sync` directory
in your current working directory. You need to be in the
`tox-pip-sync` directory for the rest of the installation
process:

```terminal
cd tox-pip-sync
```

#### Run the tests

```terminal
make test
```

#### Developing locally

Testing and developing `tox-pip-sync` can be a bit tricky, but you can get a
representative system to local testing with a bit of `tox` know how.

`tox` handles creating the `.tox/.tox` virtual env itself, and doesn't ask us
to get involved at all. This sounds like a problem, but it's actually pretty
handy for us as it allows the following workflow:

 * Add `tox-pip-sync` to your `tox.ini` of choice as normal (or use this project)
 * Run any `tox` command to ensure the `.tox/.tox` env is created
 * Install the library in editable mode `.tox/.tox/bin/pip install -e .`
 * Run commands as normal...

As we installed in editable mode, any changes should be immediately visible.

Because tox is monitoring the requirements (not us) it will only recreate the
tox env if:

 * It gets deleted or you ask `tox` to recreate the envs
 * The contents of the `requires =` section changes

This means you can run commands to your hearts content and your local
`tox-pip-sync` should never be removed.

**That's it!** You’ve finished setting up your `tox-pip-sync`
development environment. Run `make help` to see all the commands that're
available for linting, code formatting, packaging, etc.

### Updating the Cookiecutter scaffolding

This project was created from the
https://github.com/hypothesis/h-cookiecutter-pypackage/ template.
If h-cookiecutter-pypackage itself has changed since this project was created, and
you want to update this project with the latest changes, you can "replay" the
cookiecutter over this project. Run:

```terminal
make template
```

**This will change the files in your working tree**, applying the latest
updates from the h-cookiecutter-pypackage template. Inspect and test the
changes, do any fixups that are needed, and then commit them to git and send a
pull request.

If you want `make template` to skip certain files, never changing them, add
these files to `"options.disable_replay"` in
[`.cookiecutter.json`](.cookiecutter.json) and commit that to git.

If you want `make template` to update a file that's listed in `disable_replay`
simply delete that file and then run `make template`, it'll recreate the file
for you.
