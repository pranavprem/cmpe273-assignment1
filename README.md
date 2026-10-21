# CMPE 273 Assignment 1

A small Flask service that reads configuration files from a GitHub repository and serves them over HTTP. Ask for a file by name. If that exact file is missing but the other format exists, the service converts YAML to JSON or JSON to YAML and returns the conversion.

```sh
python app.py https://github.com/sithu/assignment1-config-example
curl http://127.0.0.1:5000/v1/dev-config.yml
curl http://127.0.0.1:5000/v1/dev-config.json
```

There is no HTML interface. The API responds with the file body, or with pretty-printed JSON when it converts YAML.

## Original context

This is Assignment 1 from **CMPE 273, Spring 2017**, at San Jose State University, taught by Prof. Sithu Aung. Pranav Prem wrote it in March 2017. The last commit before this refresh was 17 March 2017.

The assignment had two parts:

1. Dockerize a one-route Flask app.
2. Make the app take a GitHub repository URL on the command line and serve that repo's config files at `/v1/<file>`, in both YAML and JSON. The sample repository is [sithu/assignment1-config-example](https://github.com/sithu/assignment1-config-example). The course write-up lived at [sithu/cmpe273-spring17 assignment1](https://github.com/sithu/cmpe273-spring17/tree/master/assignment1).

The README that was committed with the assignment was a copy of that write-up. This file describes the project that was actually turned in.

The sample config repo only contains YAML (`dev-config.yml`, `test-config.yml`). Requesting the `.json` name is what exercises the converter.

## How it works

`python app.py <github-repo-url>` parses the URL, opens that repository through the GitHub API, and listens on port 5000.

`GET /v1/<config_file>` then:

1. Fetches that path from the repository and returns the file bytes decoded as UTF-8. A file that is already there is returned as stored, not reformatted.
2. If GitHub returns 404 and the name ends in `.json`, it fetches `<name>.yml`, parses it, and returns pretty JSON.
3. If the name ends in `.yml`, it fetches `<name>.json` and returns the YAML line the original program produced (flow style, wrapping braces removed).
4. Otherwise it returns a short plain-text error. Those errors are HTTP 200, which is how the 2017 app behaved.

The repository is chosen once, at process start. Later commits in that repo show up on the next request because each request calls the GitHub API again. Restart the process to point it at a different repository.

Anonymous API calls are limited to 60 requests per hour per IP. Set `GITHUB_TOKEN` to a personal access token with read access to the repository contents and the limit rises to the authenticated quota. The token is optional. The process never reads a password from the command line or from the source tree.

## Run it today

Python 3.12 is the version this refresh is tested with. Python 2.7, which the original `Dockerfile` used, is end of life and the `python:2.7.13` image is not a practical base anymore.

### Local

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py https://github.com/sithu/assignment1-config-example
```

In another shell:

```sh
curl -sS http://127.0.0.1:5000/v1/dev-config.yml
curl -sS http://127.0.0.1:5000/v1/dev-config.json
curl -sS http://127.0.0.1:5000/v1/test-config.yml
```

`dev-config.yml` from the sample repo comes back unchanged:

```yaml
welcome_message: "Hello from Dockerized Flask App"

another_config: "foo bar"
```

`dev-config.json` is converted from that YAML:

```json
{
  "welcome_message": "Hello from Dockerized Flask App",
  "another_config": "foo bar"
}
```

`test-config.yml` is:

```yaml
welcome_message: "Hello from Dockerized Flask App Test"
```

Optional environment variables:

| Variable | Effect |
| --- | --- |
| `GITHUB_TOKEN` | Authenticates the GitHub API client. Leave it unset to stay anonymous. |
| `FLASK_DEBUG` | Set to `1` to turn on Flask's debugger and reloader. The default is off. |

The server binds to `0.0.0.0:5000` so a container can publish the port. It is Flask's built-in development server, the same one the assignment used.

### Docker

```sh
docker build -t assignment1-flask-app .
docker run --rm -p 5000:5000 assignment1-flask-app
```

The image's default URL is the sample config repo above. Pass a different URL to override it:

```sh
docker run --rm -p 5000:5000 assignment1-flask-app https://github.com/sithu/assignment1-config-example
```

Pass a token at runtime without baking it into the image:

```sh
docker run --rm -p 5000:5000 -e GITHUB_TOKEN assignment1-flask-app
```

### Tests and lint

```sh
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

GitHub Actions runs those three commands on Python 3.12.

## Tech stack

- Python 3.12
- Flask 3.1
- PyGithub 2.10
- PyYAML 6.0
- Docker (`python:3.12-slim`)
- pytest and ruff for tests and lint

Direct and transitive versions are pinned in `requirements.txt`. Test and lint pins are in `requirements-dev.txt`.

## Project structure

```
app.py                     Flask app and GitHub client
tests/test_app.py          Unit tests with a fake GitHub client
requirements.txt           Pinned runtime dependencies
requirements-dev.txt       Test and lint dependencies
Dockerfile                 Python 3.12 image
pyproject.toml             pytest and ruff settings
.github/workflows/ci.yml   Lint and test on push and pull request
AGENTS.md                  Notes for coding agents
CLAUDE.md                  Pointer to AGENTS.md
```

## Sample responses

These are the bodies the sample config repo produces. The YAML responses are the files as committed. The JSON responses are converted, because that repo has no `.json` files.

`GET /v1/dev-config.yml`

```yaml
welcome_message: "Hello from Dockerized Flask App"

another_config: "foo bar"
```

`GET /v1/dev-config.json`

```json
{
  "welcome_message": "Hello from Dockerized Flask App",
  "another_config": "foo bar"
}
```

`GET /v1/test-config.json`

```json
{
  "welcome_message": "Hello from Dockerized Flask App Test"
}
```
