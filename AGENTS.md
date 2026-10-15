# Agent guide

CMPE 273 (San Jose State, Spring 2017) Assignment 1. A single-file Flask app serves config files from one GitHub repository. Read this file before changing behavior. [CLAUDE.md](CLAUDE.md) only points here.

## Architecture

- `python app.py <github-repo-url>` is the only entrypoint. Importing `app` does not read `sys.argv` and does not open a socket.
- `parse_github_url` finds the first `/`-separated segment containing `github` and treats the next two segments as owner and repo. That substring check is the 2017 heuristic. Keep it.
- `create_app` connects to GitHub once, at startup. A bad URL or a missing repo does not crash the process. The view returns the error string on every request.
- `GET /v1/<config_file>` calls `get_required_response`. The path converter does not match slashes, so nested paths are out of scope.
- A file that exists is returned verbatim (`decoded_content` as UTF-8), including quotes and blank lines. Do not re-serialize it.
- Missing `.json` loads `<stem>.yml` and returns `json.dumps(..., indent=2)` plus a trailing newline, `Content-Type: application/json`. That matches Flask 0.12's pretty `jsonify` output for curl.
- Missing `.yml` loads `<stem>.json` and returns `json_to_yml`. PyYAML 3 emitted `{key: value}\n` and the original code sliced off the braces. `json_to_yml` still does that slice, and it forces `default_flow_style=True` so modern PyYAML does not emit block style (which the slice would corrupt).
- The stem split is on the last dot (`env.prod.json` -> `env.prod.yml`).
- Extensions other than `.yml` and `.json` are not converted. `.yaml` is not an alias.
- Error bodies stay HTTP 200 plain text. The two rate-limit strings differ by a final period on purpose; they are the original messages.
- `GITHUB_TOKEN`, when set and non-blank, is passed as `Auth.Token`. There is no password parameter. Do not add one.
- `FLASK_DEBUG=1` enables Flask's debugger. The default is off because the server binds to `0.0.0.0`.

## Commands

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
ruff format .
pytest
python app.py https://github.com/sithu/assignment1-config-example
```

Runtime pins live in `requirements.txt` (a full `pip freeze`, direct packages Flask, PyGithub, and PyYAML). Dev pins live in `requirements-dev.txt`. Docker installs only `requirements.txt`. CI is `.github/workflows/ci.yml` on Python 3.12: ruff check, ruff format --check, pytest.

Tests must not call the network. Pass a fake `github_client` into `create_app`. `build_github_client` is the only helper that constructs a real `Github`.

## Conventions

- Keep the app as one module, `app.py`. The assignment was a three-file hand-in (`app.py`, `requirements.txt`, `Dockerfile`).
- Preserve the response bodies and the error strings covered by `tests/test_app.py`. Change them only when you mean to, and update the tests in the same commit.
- New Python is 3.12. The original `Dockerfile` used `python:2.7.13` and the original code used `basestring` and `str.decode("base64")`.
- Ruff is the formatter and linter (`pyproject.toml`, line length 100). Don't add a second formatter.
- No license file. Don't add one.

## Gotchas

- Anonymous GitHub calls fail with the rate-limit string after 60 requests an hour. A live smoke test against `sithu/assignment1-config-example` spends several of those.
- `get_contents` is one API call per file. The 2017 code called `get_file_contents` and `get_contents` for the same path. Don't put the double fetch back. `get_file_contents` is gone from current PyGithub.
- Startup performs `get_user` + `get_repo` before `app.run`. A hanging network there delays boot. The server still comes up if that call raises; the view returns the message.
- Docker's default command is the sample config repo, not this repository. This repository has no config files. Override by passing a URL after the image name (`ENTRYPOINT` is `python app.py`).
- The image runs as uid 10001 and does not write `.pyc` (`PYTHONDONTWRITEBYTECODE`).
- A GitHub account password for `pranavprem` was committed in `509c5e8` and removed from the tree in `4f32508`. It is still in git history. Never copy it back into the source, the Docker image, tests, or docs. GitHub no longer accepts account passwords for the API. The owner should rotate that password if the account, or any place the password was reused, still exists.
- Don't rewrite git history unless the owner asks.
