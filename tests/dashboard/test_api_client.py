from unittest.mock import Mock, patch

from dashboard import api_client


def test_uses_embedded_api_when_base_url_is_not_configured(monkeypatch):
    monkeypatch.setattr(api_client, "BASE_URL", None)
    response = Mock()
    response.json.return_value = {"status": "ok"}
    client = Mock()
    client.request.return_value = response

    with patch.object(api_client, "_embedded_client", return_value=client):
        assert api_client.get("/health") == {"status": "ok"}

    client.request.assert_called_once_with("GET", "/health", params={})
    response.raise_for_status.assert_called_once_with()


def test_uses_external_api_when_base_url_is_configured(monkeypatch):
    monkeypatch.setattr(api_client, "BASE_URL", "https://api.example.com/")
    response = Mock()
    response.json.return_value = {"status": "ok"}

    with patch.object(api_client.requests, "request", return_value=response) as request:
        assert api_client.get("/health") == {"status": "ok"}

    request.assert_called_once_with(
        "GET", "https://api.example.com/health", timeout=30, params={}
    )
    response.raise_for_status.assert_called_once_with()
