from hdhelpers.plotting import resolve_color


def test_resolve_color():
    assert resolve_color("ki.vision.bright") == "#ffb058"
    assert resolve_color("red") == "red"
    assert resolve_color("#feb0e8") == "#feb0e8"
