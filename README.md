# hdhelpers
## What is hdhelpers?
hdhelpers is a package designed for and included in the standard installation of the [hetida
designer](https://github.com/hetida/hetida-designer).

## Getting Started with hdhelpers
Since the intended use of the hdhelpers package is as a part of the hetida designer, it is highly recommended to follow
the [hetida designer setup guide](https://github.com/hetida/hetida-designer/blob/release/README.md#getting-started-with-hetida-designer).

For a specific example of how to use hdhelpers functionality in a hetida designer component, see [Example](#example).

## Developing for hdhelpers
For dependency management and venv setup, building and publishing, [uv](https://docs.astral.sh/uv/) is used.

### Setting up a Development Environment
1) Create a virtual environment with `uv venv`. This will create a hidden `.venv` directory.
2) Activate the virtual environment via `source .venv/bin/activate`
3) Run `uv sync --all-extras` to install all dependencies given in pyproject.toml.
4) In case you need to add a new dependency, do so via `uv add <new_dependency>`. That way, uv finds versions of all
   dependencies that are compatible with each other.
5) In case you need a new requirement for development purposes please use `uv add --dev <new_dependency>`

Note: To install hdhelpers in editable mode in your venv please run `uv pip install -e .`

### Code Quality
Once you are done writing your code, including unit tests, use `./run check` to see if your code quality is sufficient.

### Documentation
Fr documentation we use the tool sphinx. Please apply `run create_docu` to create the current state of documentation. It will be stored in **docs/build**.

### Build, Release and Publish
This process is usually triggered when a PR from develop to main is created.

To **build** and **release** a new package version

1) Please execute `./run build_package <version_nr>` where version number should follow [semantic versioning](https://semver.org/).
This will:
- Runs `uv lock --upgrade` to upgrade dependencies.
- Update version in pyproject.toml
- Update __version__ in __init__.py
- Builds wheels of hdhelpers in ./dist

2) Ensure that listed `classifiers` in `pyproject.toml`are up to date. If not
- Update pyproject.toml accordingly
- Update `./run test-py-versions` accordingly for local testing using uv
- Update `check_pull_request.yml` accordingly for automated pipeline execution of checks

3) Update CHANGELOG.md manually


When the PR is accepted, the package can be published. To **publish** the build from the `dist` subdirectory to PyPI,

1) tag your main branch with the specified package version using github interface

2) use `uv publish`. To do so, you need a PyPI account with a token to enter in the command line as password following the username "\_\_token__",
and you need maintainer or owner access to the [hdhelpers PyPI project](https://pypi.org/project/hdhelpers/).

3) After publishing please communicate to the hetida designer team so upgrade there dependencies.
The hetida designer docker compose setup installs hdhelpers from [PyPI](https://pypi.org) as it does with any dependency listed in `runtime/requirements.in`.


### Trouble Shooting
- Please ensure that dependencies specified for hdhelpers do work in current designer versions.
