.PHONY: help
help:
	@echo "make help              Show this help message"
	@echo "make lint              Code quality analysis (pylint)"
	@echo "make format            Correctly format the code"
	@echo "make checkformatting   Crash if the code isn't correctly formatted"
	@echo "make dist              Create package in the dist/ directory for local testing"
	@echo "make release           Tag a release and trigger deployment to PyPI"
	@echo "make initialrelease    Create the first release of a package"
	@echo "make test              Run the unit tests"
	@echo "make testall           Run the unit tests against all versions of Python"
	@echo "make sure              Make sure that the formatter, linter, tests, etc all pass"
	@echo "make coverage          Print the unit test coverage report"

.PHONY: lint
lint: python
	@tox -qe lint

.PHONY: format
format: python
	@tox -qe format

.PHONY: checkformatting
checkformatting: python
	@tox -qe checkformatting

.PHONY: dist
dist: python
	@BUILD=$(BUILD) tox -qe dist

.PHONY: release
release: python
	@tox -qe release

.PHONY: initialrelease
initialrelease: python
	@tox -qe initialrelease

.PHONY: test
test: python
	@tox -qe `hdev python_version --style tox --first`-tests

.PHONY: testall
testall: python
	@tox -qe \{`hdev python_version --style tox --include-future`\}-tests

.PHONY: sure
sure: checkformatting lint test coverage

.PHONY: coverage
coverage: python
	@tox -qe coverage

.PHONY: python
python:
	@# Ensure we can run even if the local pyenv versions are not installed
	@PYENV_VERSION=system hdev install-python;
