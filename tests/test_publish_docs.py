"""Checks for synchronizing generated documentation."""

import runpy
from pathlib import Path

import pytest

publish_docs = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "sphinx" / "publish_docs.py")
)["publish_docs"]


def test_publish_replaces_generated_files_and_preserves_local_files(tmp_path):
    source = tmp_path / "html"
    destination = tmp_path / "docs"
    (source / "_static").mkdir(parents=True)
    (source / "index.html").write_text("new index")
    (source / "_static" / "stylesheet.css").write_text("new style")
    (destination / "_static").mkdir(parents=True)
    (destination / "_static" / "sidebar-tooltip.js").write_text("obsolete")
    (destination / "_static" / "stylesheet.css").write_text("old style")
    (destination / "old_page.html").write_text("obsolete")
    (destination / ".nojekyll").touch()
    (destination / "notes.md").write_text("local notes")
    (destination / "build").mkdir()
    (destination / "build" / "preview.html").write_text("local preview")

    publish_docs(source, destination)

    assert (destination / "index.html").read_text() == "new index"
    assert (destination / "_static" / "stylesheet.css").read_text() == "new style"
    assert not (destination / "_static" / "sidebar-tooltip.js").exists()
    assert not (destination / "old_page.html").exists()
    assert (destination / ".nojekyll").exists()
    assert (destination / "notes.md").read_text() == "local notes"
    assert (destination / "build" / "preview.html").read_text() == "local preview"


def test_publish_rejects_incomplete_build_before_changing_destination(tmp_path):
    source = tmp_path / "html"
    destination = tmp_path / "docs"
    source.mkdir()
    destination.mkdir()
    (destination / "index.html").write_text("published index")

    with pytest.raises(ValueError, match="no index.html"):
        publish_docs(source, destination)

    assert (destination / "index.html").read_text() == "published index"


def test_publish_rejects_overlapping_directories(tmp_path):
    (tmp_path / "index.html").write_text("published index")

    with pytest.raises(ValueError, match="must not overlap"):
        publish_docs(tmp_path, tmp_path / "docs")

    assert (tmp_path / "index.html").read_text() == "published index"
