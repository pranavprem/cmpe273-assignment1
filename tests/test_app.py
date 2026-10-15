"""Behavior tests for the config service. GitHub is faked; nothing here uses the network."""

import pytest
from github import Auth, RateLimitExceededException, UnknownObjectException

from app import (
    EXAMPLE_REPO_URL,
    NOT_GITHUB,
    RATE_LIMIT_FETCH,
    RATE_LIMIT_STARTUP,
    REPO_MISSING,
    build_github_client,
    create_app,
    main,
    parse_github_url,
)

DEV_YML = 'welcome_message: "Hello from Dockerized Flask App"\n\nanother_config: "foo bar"\n'
DEV_JSON = (
    '{\n  "welcome_message": "Hello from Dockerized Flask App",\n  "another_config": "foo bar"\n}\n'
)


class FakeContent:
    def __init__(self, text: str):
        self.decoded_content = text.encode("utf-8")


class FakeRepo:
    def __init__(self, files: dict[str, str]):
        self.files = files

    def get_contents(self, path: str):
        if path not in self.files:
            raise UnknownObjectException(404, {"message": "Not Found"}, None)
        return FakeContent(self.files[path])


class FakeGithub:
    def __init__(self, repo: FakeRepo, repo_name: str = "configs"):
        self.repo = repo
        self.repo_name = repo_name
        self.requested = None

    def get_user(self, user: str):
        self.requested = (user, None)
        return self

    def get_repo(self, name: str):
        self.requested = (self.requested[0] if self.requested else None, name)
        if name != self.repo_name:
            raise UnknownObjectException(404, {"message": "Not Found"}, None)
        return self.repo


def client_for(files: dict[str, str], url: str = "https://github.com/someone/configs"):
    github = FakeGithub(FakeRepo(files))
    application = create_app(url, github_client=github)
    return application.test_client(), github


def test_parse_assignment_url():
    assert parse_github_url(EXAMPLE_REPO_URL) == ("sithu", "assignment1-config-example")


def test_parse_strips_git_suffix_query_and_trailing_slash():
    url = "https://github.com/someone/configs.git?tab=readme#top"
    assert parse_github_url(url) == ("someone", "configs")
    assert parse_github_url("https://github.com/someone/configs/") == ("someone", "configs")


def test_parse_rejects_non_github_and_incomplete_urls():
    assert parse_github_url("https://gitlab.com/someone/configs") is None
    assert parse_github_url("https://github.com/only-owner") is None
    assert parse_github_url("https://github.com//configs") is None


def test_returns_existing_file_unchanged():
    client, _github = client_for({"dev-config.yml": DEV_YML, "dev-config.json": '{"b":1,"a":2}'})

    yml = client.get("/v1/dev-config.yml")
    raw_json = client.get("/v1/dev-config.json")

    assert yml.status_code == 200
    assert yml.data.decode() == DEV_YML
    assert yml.mimetype == "text/html"
    assert raw_json.data.decode() == '{"b":1,"a":2}'
    assert raw_json.mimetype == "text/html"


def test_converts_yml_to_pretty_json_when_json_is_missing():
    client, _github = client_for({"dev-config.yml": DEV_YML})

    response = client.get("/v1/dev-config.json")

    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.data.decode() == DEV_JSON
    assert response.get_json() == {
        "welcome_message": "Hello from Dockerized Flask App",
        "another_config": "foo bar",
    }


def test_converts_json_to_flow_yaml_when_yml_is_missing():
    client, _github = client_for(
        {
            "dev-config.json": (
                '{"welcome_message": "Hello from Dockerized Flask App", '
                '"another_config": "foo bar"}\n'
            )
        }
    )

    response = client.get("/v1/dev-config.yml")

    assert response.status_code == 200
    assert response.data.decode() == (
        "welcome_message: Hello from Dockerized Flask App, another_config: foo bar"
    )


def test_fallback_uses_the_last_extension():
    client, _github = client_for({"env.prod.yml": "size: 1\n"})

    response = client.get("/v1/env.prod.json")

    assert response.get_json() == {"size": 1}


def test_missing_file_messages():
    client, _github = client_for({"dev-config.yml": DEV_YML})

    assert client.get("/v1/missing.json").data.decode().startswith("File not found")
    assert client.get("/v1/no-extension").data.decode() == "File not found"
    assert client.get("/v1/dev-config.txt").data.decode() == "File not found"


def test_startup_errors_are_served_on_each_request():
    missing = create_app(
        "https://github.com/someone/missing",
        github_client=FakeGithub(FakeRepo({}), repo_name="configs"),
    )
    not_github = create_app("https://gitlab.com/someone/configs")
    limited = create_app(
        "https://github.com/someone/configs",
        github_client=_RaisingGithub(RateLimitExceededException(403, {"message": "limit"}, None)),
    )
    broken = create_app(
        "https://github.com/someone/configs",
        github_client=_RaisingGithub(RuntimeError("boom")),
    )

    assert missing.test_client().get("/v1/dev-config.yml").data.decode() == REPO_MISSING
    assert not_github.test_client().get("/v1/dev-config.yml").data.decode() == NOT_GITHUB
    assert limited.test_client().get("/v1/dev-config.yml").data.decode() == RATE_LIMIT_STARTUP
    assert broken.test_client().get("/v1/dev-config.yml").data.decode() == (
        "Please contact the developer for error: boom"
    )


def test_fetch_errors_keep_the_original_messages():
    class RateLimitedRepo(FakeRepo):
        def get_contents(self, path: str):
            raise RateLimitExceededException(403, {"message": "limit"}, None)

    class BrokenRepo(FakeRepo):
        def get_contents(self, path: str):
            raise RuntimeError("disk")

    rate_client = create_app(
        "https://github.com/someone/configs",
        github_client=FakeGithub(RateLimitedRepo({})),
    ).test_client()
    broken_client = create_app(
        "https://github.com/someone/configs",
        github_client=FakeGithub(BrokenRepo({})),
    ).test_client()

    assert rate_client.get("/v1/dev-config.yml").data.decode() == RATE_LIMIT_FETCH
    assert broken_client.get("/v1/dev-config.yml").data.decode() == (
        "Please contact the developer for error: disk"
    )


def test_git_suffix_is_passed_to_github_without_the_suffix():
    _client, github = client_for({}, url="https://github.com/someone/configs.git")

    response = _client.get("/v1/dev-config.yml")

    assert github.requested == ("someone", "configs")
    assert response.data.decode().startswith("File not found")


def test_root_has_no_route():
    client, _github = client_for({})
    assert client.get("/").status_code == 404


def test_build_github_client_reads_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    client = build_github_client()
    assert isinstance(client.requester.auth, Auth.Token)
    assert client.requester.auth.token == "test-token"

    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    assert build_github_client().requester.auth is None


def test_main_requires_exactly_one_url(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    assert "usage:" in capsys.readouterr().err


class _RaisingGithub:
    def __init__(self, error: Exception):
        self.error = error

    def get_user(self, user: str):
        raise self.error
