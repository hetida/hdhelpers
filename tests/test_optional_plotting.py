import os
import subprocess
import sys

# None in sys.modules makes every import of plotly fail, as if it was not installed
WITHOUT_PLOTLY = "import sys; sys.modules['plotly'] = None\n"


def run_without_plotly(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", WITHOUT_PLOTLY + code],
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONPATH": os.pathsep.join(sys.path)},
        check=False,
    )


def test_hdhelpers_works_without_plotly() -> None:
    result = run_without_plotly(
        "import hdhelpers, hdhelpers.metadata\n"
        "from hdhelpers import StatusColors, get_locale, modify_timezone\n"
        "from hdhelpers.metadata.conventions import check_metadata_conventions\n"
    )
    assert result.returncode == 0, result.stderr


def test_plotting_names_need_the_plotting_extra() -> None:
    result = run_without_plotly("from hdhelpers import set_dt_ticks\n")

    assert result.returncode != 0
    assert "hdhelpers[plotting]" in result.stderr


def test_plotting_names_need_the_plotting_extra_on_every_access() -> None:
    # twice, since a failed import keeps the modules imported until then, e.g. the colors
    result = run_without_plotly(
        "import hdhelpers\n"
        "for name in sorted(hdhelpers._PLOTTING_NAMES | {'plotting'}) * 2:\n"
        "    try:\n"
        "        getattr(hdhelpers, name)\n"
        "    except ImportError as e:\n"
        "        assert 'hdhelpers[plotting]' in str(e), e\n"
        "    else:\n"
        "        raise SystemExit(f'hdhelpers.{name} is available without plotly')\n"
    )

    assert result.returncode == 0, result.stderr


def test_plotting_names_are_available_with_plotly() -> None:
    import hdhelpers  # noqa: PLC0415
    from hdhelpers.plotting.timestamp_ticks import set_dt_ticks  # noqa: PLC0415

    assert hdhelpers.set_dt_ticks is set_dt_ticks
    assert "set_dt_ticks" in dir(hdhelpers)
