from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_serves_page_with_comfy_theme():
    response = client.get("/")
    assert response.status_code == 200
    assert "/themes/comfy.css" in response.text


def test_comfy_theme_sets_all_variables():
    css = client.get("/themes/comfy.css").text
    for name in ("--bg", "--panel", "--text", "--muted", "--accent",
                 "--font-ui", "--font-mono", "--radius"):
        assert name in css


def test_base_css_and_htmx_are_served():
    assert client.get("/static/base.css").status_code == 200
    assert client.get("/static/vendor/htmx.min.js").status_code == 200
