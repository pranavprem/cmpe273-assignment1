"""CMPE 273 Spring 2017 Assignment 1.

Serve YAML and JSON configuration files from a GitHub repository. The repository
URL is chosen once, when the process starts, and every ``GET /v1/<file>`` reads
the latest copy of that file from GitHub.
"""

from __future__ import annotations

import json
import os
import sys

import yaml
from flask import Flask, Response
from github import Auth, Github, RateLimitExceededException, UnknownObjectException

NOT_GITHUB = "url supplied is not github"
REPO_MISSING = "repository does not exist. Please check link supplied"
RATE_LIMIT_STARTUP = "You have reached your github rate limit. Try after an hour."
RATE_LIMIT_FETCH = "You have reached your github rate limit. Try after an hour"
EXAMPLE_REPO_URL = "https://github.com/sithu/assignment1-config-example"
USAGE = f"usage: python app.py <github-repo-url>\nexample: python app.py {EXAMPLE_REPO_URL}"


def parse_github_url(repo_url: str) -> tuple[str, str] | None:
    """Return ``(owner, repo)`` from an https GitHub URL, or None.

    The original assignment looked for the first path segment containing
    "github" and took the next two segments as the owner and repository.
    """
    parts = repo_url.split("/")
    for index, part in enumerate(parts):
        if "github" not in part:
            continue
        if index + 2 >= len(parts):
            return None
        user = parts[index + 1].strip()
        repo = parts[index + 2].split("?", 1)[0].split("#", 1)[0].strip()
        if repo.endswith(".git"):
            repo = repo[: -len(".git")]
        if not user or not repo:
            return None
        return user, repo
    return None


def build_github_client() -> Github:
    """Use ``GITHUB_TOKEN`` when it is set; otherwise call the API anonymously."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return Github(auth=Auth.Token(token))
    return Github()


def read_text(repo, path: str) -> str:
    """Read one file from the connected repository as UTF-8 text."""
    contents = repo.get_contents(path)
    return contents.decoded_content.decode("utf-8")


def json_to_yml(text: str) -> str:
    """Convert JSON text to the YAML string this app returned in 2017.

    PyYAML 3 dumped small mappings in flow style (``{key: value}\\n``). The
    original code then dropped the wrapping braces and the trailing newline.
    PyYAML 5.1+ dumps block style by default, which would make that slice cut
    the first character off, so flow style is requested explicitly.
    """
    dumped = yaml.safe_dump(
        json.loads(text),
        default_flow_style=True,
        sort_keys=False,
        width=4096,
    )
    if dumped.startswith("{") and dumped.endswith("}\n"):
        return dumped[1:-2]
    return dumped.rstrip("\n")


def yml_to_json_response(text: str) -> Response:
    """Convert YAML text to the pretty JSON body Flask produced for curl in 2017."""
    body = json.dumps(yaml.safe_load(text), indent=2) + "\n"
    return Response(body, mimetype="application/json")


def get_required_response(repo, config_file: str):
    """Return the requested file, or the other format converted into it."""
    try:
        return read_text(repo, config_file)
    except UnknownObjectException:
        if "." not in config_file:
            return "File not found"
        filename, extension = config_file.rsplit(".", 1)
        try:
            if extension == "json":
                return yml_to_json_response(read_text(repo, f"{filename}.yml"))
            if extension == "yml":
                return json_to_yml(read_text(repo, f"{filename}.json"))
            return "File not found"
        except Exception as error:
            return f"File not found {error}"
    except RateLimitExceededException:
        return RATE_LIMIT_FETCH
    except Exception as error:
        return f"Please contact the developer for error: {error}"


def connect(repo_url: str, github_client=None):
    """Open the repository, or return the same error string the app serves."""
    parsed = parse_github_url(repo_url)
    if parsed is None:
        return NOT_GITHUB
    user, repo_name = parsed
    client = github_client or build_github_client()
    try:
        return client.get_user(user).get_repo(repo_name)
    except UnknownObjectException:
        return REPO_MISSING
    except RateLimitExceededException:
        return RATE_LIMIT_STARTUP
    except Exception as error:
        return f"Please contact the developer for error: {error}"


def create_app(repo_url: str, github_client=None) -> Flask:
    """Build the Flask app and connect to ``repo_url`` before serving."""
    app = Flask(__name__)
    git = connect(repo_url, github_client)

    @app.route("/v1/<config_file>")
    def controller(config_file: str):
        if isinstance(git, str):
            return git
        return get_required_response(git, config_file)

    return app


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(USAGE, file=sys.stderr)
        raise SystemExit(2)
    debug = os.environ.get("FLASK_DEBUG", "").strip() in {"1", "true", "True"}
    create_app(args[0]).run(debug=debug, host="0.0.0.0")


if __name__ == "__main__":
    main()
