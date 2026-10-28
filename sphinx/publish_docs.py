"""Synchronize generated documentation while preserving repository and local files."""

from pathlib import Path


def publish_docs(source: Path, destination: Path) -> None:
    """Copy a validated HTML build and remove obsolete Sphinx output files."""
    source = source.resolve(strict=True)
    destination = destination.resolve()
    if not (source / "index.html").is_file():
        raise ValueError("The documentation build has no index.html.")
    if source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("The build and publication directories must not overlap.")

    files = {
        path.relative_to(source): path
        for path in source.rglob("*")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(source).parts)
    }
    existing = [path for path in destination.glob("*.html") if path.is_file()]
    existing += [destination / "objects.inv", destination / "searchindex.js"]
    for name in ("_static", "_sources", "_modules", "_images", "_downloads"):
        existing += [path for path in (destination / name).rglob("*") if path.is_file()]

    # Validate all write/delete targets before modifying the published documentation.
    targets = [*existing, *(destination / relative for relative in files)]
    if any(not path.resolve().is_relative_to(destination) for path in targets):
        raise ValueError("A documentation target points outside the publication directory.")

    for path in existing:
        if path.is_file() and path.relative_to(destination) not in files:
            path.unlink()
    for relative, path in files.items():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        if path.suffix in {".html", ".txt", ".css", ".js"}:
            data = data.replace(b"\r\n", b"\n")
        if path.suffix == ".html":
            data = b"\n".join(line.rstrip(b" \t") for line in data.split(b"\n"))
        if not target.is_file() or target.read_bytes() != data:
            target.write_bytes(data)


if __name__ == "__main__":
    repository = Path(__file__).resolve().parent.parent
    publish_docs(repository / "sphinx" / "build" / "html", repository / "docs")
