import json
from unittest.mock import patch

from tick.geo import lookup_timezone


def _mock_response(data):
    """Create a mock urllib response context manager."""
    from io import BytesIO
    from unittest.mock import MagicMock

    body = BytesIO(json.dumps(data).encode())
    resp = MagicMock()
    resp.read = body.read
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestLookupTimezone:
    @patch("tick.geo.urllib.request.urlopen")
    def test_successful_lookup(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response(
            {"results": [{"timezone": "America/Sao_Paulo"}]}
        )
        assert lookup_timezone("Brasil") == "America/Sao_Paulo"

    @patch("tick.geo.urllib.request.urlopen")
    def test_empty_results(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({"results": []})
        assert lookup_timezone("Nonexistent") is None

    @patch("tick.geo.urllib.request.urlopen")
    def test_no_results_key(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response({})
        assert lookup_timezone("Nonexistent") is None

    @patch("tick.geo.urllib.request.urlopen")
    def test_network_error(self, mock_urlopen):
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("connection refused")
        assert lookup_timezone("Brasil") is None
