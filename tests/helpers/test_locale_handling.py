from unittest.mock import MagicMock, patch

from hdhelpers.helpers import get_locale
from hdhelpers.plot_target_settings import PlotTargetSettings


def test_get_locale():
    assert get_locale("de") == "de"
    assert get_locale("de_DE") == "de-DE"

    plot_target_settings_mock = MagicMock(
        return_value=PlotTargetSettings(plot_target_locale="en_US")
    )
    with patch(
        "hdhelpers.plot_target_settings.get_plot_target_settings", plot_target_settings_mock
    ):
        assert get_locale() == "en-US"
        assert get_locale("de") == "de"
