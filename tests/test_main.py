def test_index_serves_page_with_comfy_theme(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "/themes/comfy.css" in response.text


def test_comfy_theme_sets_all_variables(client):
    css = client.get("/themes/comfy.css").text
    for name in ("--bg", "--panel", "--text", "--muted", "--accent",
                 "--font-ui", "--font-mono", "--radius"):
        assert name in css


def test_base_css_and_htmx_are_served(client):
    assert client.get("/static/base.css").status_code == 200
    assert client.get("/static/vendor/htmx.min.js").status_code == 200


def test_index_shows_empty_list_and_form_with_all_types(client):
    page = client.get("/").text
    assert "No projects yet" in page
    for label in ("Game", "Utility app", "3D print"):
        assert f">{label}</option>" in page


def test_new_project_form_creates_and_lists_the_project(client, settings):
    response = client.post("/projects", data={"name": "MyGame", "type": "game", "goal": "Fun"})
    assert response.status_code == 200
    assert "MyGame" in response.text
    assert (settings.projects_root / "MyGame" / "project.yaml").is_file()
    assert "MyGame" in client.get("/").text


def test_new_project_form_shows_errors_and_keeps_input(client):
    client.post("/projects", data={"name": "MyGame", "type": "game"})
    duplicate = client.post("/projects", data={"name": "MyGame", "type": "game"})
    assert "already exists" in duplicate.text
    assert 'value="MyGame"' in duplicate.text

    unknown = client.post("/projects", data={"name": "Other", "type": "nope"})
    assert "Pick a project type" in unknown.text
