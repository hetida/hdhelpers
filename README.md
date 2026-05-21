# Welcome to hdhelpers

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/hetida/hdhelpers/graphs/commit-activity)
[![build](https://github.com/hetida/hdhelpers/actions/workflows/check_pull_request.yml/badge.svg)](https://github.com/hetida/hdhelpers/actions/workflows/check_pull_request.yml)
![python](https://img.shields.io/badge/python-%203.12%20|%203.13|%203.14%20-blue)
[![PyPI version](https://badge.fury.io/py/hdhelpers.svg)](https://badge.fury.io/py/hdhelpers)
![PyPI - License](https://img.shields.io/pypi/l/hdhelpers)
[![Downloads](https://pepy.tech/badge/hdhelpers)](https://pepy.tech/project/hdhelpers)

## What is hdhelpers?
hdhelpers is a package designed for and included in the standard installation of the [hetida
designer](https://github.com/hetida/hetida-designer).

Currently, the package provides functions to retrieve metadata from Pandas objects (stored in the `attr` of the Pandas object). Pandas objects are the standard for processing time series data in the hetida designer. Additionally, a function is provided to handle time zone information. In the future, the package is planned to be expanded, for example by providing functions to facilitate visualization.

The documentation of the package is a [GitHub page](https://hetida.github.io/hdhelpers/), on which the functions of the package are described and some tips for getting started with using the package are given.

## Getting Started with hdhelpers
Since version >0.13.10 the hetida designer runtime comes with an installed version of hdhelpers. To start the hetida designer we recommend following the [hetida designer setup guide](https://github.com/hetida/hetida-designer/blob/release/README.md#getting-started-with-hetida-designer).

An example is given in [GitHub page](https://hetida.github.io/hdhelpers/first_steps.html#how-to-get-metadata-with-hdhelpers) of how to use functionalities of hdhelpers inside a hetida designer component. Furthermore the base component [Single Time Series Plot](https://github.com/hetida/hetida-designer/blob/release/runtime/transformations/components/visualization) uses hdhelpers to demonstrate the usage (since version >0.13.10).

## Developing for hdhelpers
For dependency management and venv setup, building and publishing, [uv](https://docs.astral.sh/uv/) is used.

### Setting up a Development Environment
#### Python environment
1) Create a virtual environment with `uv venv`. This will create a hidden `.venv` directory.
2) Activate the virtual environment via `source .venv/bin/activate`
3) Run `uv sync` to install all dependencies given in pyproject.toml.
4) In case you need to add a new dependency, do so via `uv add <new_dependency>`. That way, uv finds versions of all
   dependencies that are compatible with each other.
5) In case you need a new requirement for development purposes please use `uv add --dev <new_dependency>`

Note: To install hdhelpers in editable mode in your venv please run `uv pip install -e .`

#### hetida designer with hdhelpers
To test designer images with current hdhelpers version please save a copy of [docker-compose.yml](https://github.com/hetida/hetida-designer/blob/release/docker-compose.yml) from the hetida designer repository.

Then write a `Dockerfile` to install the current hdhelpers version in the required designer backend.
```yaml
FROM hetida/designer-backend:<<hd_version>>

USER root

RUN pip install .

USER hd_app

CMD ["bash", "/app/start.sh"]
```

Then modify the docker-compose.yml to work with the backend version defined by the modified Dockerfile.
```yaml
...
  hetida-designer-backend:
    build:
      context: .
      dockerfile: Dockerfile
...
```


use docker-compose.yaml, e.g. via
`docker compose -f 'docker-compose.yaml' up -d --build`. This compose setup loads the current
hetida designer images and installs the hdhelpers package in the runtime. Thus, you can use functions of hdhelpers
writing component code.

### Code Quality
Once you are done writing your code, including unit tests, use `./run check` to see if your code quality is sufficient.

### Documentation
For documentation we use the tool sphinx. Please apply `./run build_docs` to create the current state of documentation. It will be stored in **docs**. You can open the documentation by opening `docs/index.html`, e.g. with your browser.

### Build, Release and Publish
The first step for publishing a new package version is creating and merging a pull request from develop to main.
In detail the following steps should be executed beforehand:

1) Please execute `./run build_package <version_nr>` where version number should follow [semantic versioning](https://semver.org/).
This will:
- Runs `uv sync --frozen` to upgrade dependencies.
- Update version in pyproject.toml
- Update \_\_version__ in \_\_init__.py
- Builds wheels of hdhelpers in ./dist

2) Ensure that listed `classifiers` in `pyproject.toml`are up to date. If not
- Update `pyproject.toml` accordingly
- Update `./run test-py-versions` accordingly for local testing using uv
- Update `check_pull_request.yml` accordingly for automated pipeline execution of checks
- Update badge in this file for Python versions above

3) Update CHANGELOG.md manually following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

When the PR is accepted, the package can be **published** in a second step.
To **publish** the build from the `dist` subdirectory to PyPI,

1) tag your main branch with the specified package version

2) use `uv publish --index testpypi --token <API-token>`. You need a Test-PyPI account with a token and you need maintainer/owner access to the [hdhelpers Test-PyPI project](https://test.pypi.org/project/hdhelpers/).

3) verifiy that package can be installed by using:
```bash
uv run --with 'hdhelpers==<version>'
     --refresh-package hdhelpers
     --default-index https://test.pypi.org/simple/
     --index https://test.pypi.org/simple/
     --no-project
     -- python -c "import hdhelpers; print(hdhelpers.__version__)"
```

4) use `uv publish dist/*` to upload the package on [hdhelpers PyPI project](https://pypi.org/project/hdhelpers/).

3) After publishing please communicate to the hetida designer team so upgrade there dependencies.
The hetida designer docker compose setup installs hdhelpers from [PyPI](https://pypi.org) as it does with any dependency listed in `runtime/requirements.in`.

### Notes
- Please ensure that dependencies specified for hdhelpers do work in current designer versions.
- If you want to upgrade dependencies please run `uv lock --upgrade`
- to install hdhelpers from testpypi you can use:
`uv pip install --extra-index-url https://test.pypi.org/simple/ --index-url https://pypi.org/simple --refresh --index-strategy unsafe-best-match hdhelpers`
