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
3) Run `uv sync` to install all dependencies given in pyproject.toml.
4) In case you need to add a new dependency, do so via `uv add <new_dependency>`. That way, uv finds versions of all
   dependencies that are compatible with each other.
5) In case you need a new requirement for development purposes please use `uv add --dev <new_dependency>`
6) To check if hdhelpers is still compatible with the newest version of hetida designer run `uv pip compile requirements-package.in > requirements-package.txt` `uv pip sync requirements.txt requirements-dev.txt requirements-base.txt requirements-package.txt`

To install hdhelpers in editable mode in your venv please run `uv pip install -e .`

### Code Quality
Once you are done writing your code, including unit tests, use `./run check` to see if your code quality is sufficient.

### Documentation
Fr documentation we use the tool sphinx. Please run `sphinx-build -M html docs/source docs/build` to create the documentation which will be stroed in **hdhelpers/docs/build**

### Build, Publish, and Release
Before you build the package, set an appropriate version number in `pyproject.toml` that matches the version number in
the hetida designer `VERSION` file.

To build the package and delete any files that are currently in the `dist` subdirectory, execute `rm -r dist && uv
build`. [Hatchling](https://pypi.org/project/hatchling/), the build backend specified in `pyproject.toml`, will build a
new sdist and wheel in the `dist` subdirectory.

To publish the build from the `dist` subdirectory to PyPI, use `uv publish`. To do so, you need a PyPI account with a
token to enter in the command line as password following the username "\_\_token__", and you need maintainer or owner
access to the [hdhelpers PyPI project](https://pypi.org/project/hdhelpers/).

The hetida designer docker compose setup installs hdhelpers from [PyPI](https://pypi.org) as it does with any dependency listed in `runtime/requirements.in`.

Next time your hetida designer docker compose dev setup builds the runtime container, it will install the hdhelpers
version that you just deployed.
