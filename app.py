import sys
import json
import yaml
from flask import Flask
from flask import jsonify
from github import Github
from github import UnknownObjectException
from github import RateLimitExceededException

app = Flask(__name__)
url = sys.argv[1].split("/")


for i in range(len(url)):
    if "github" in url[i]:
        user = url[i+1]
        repo = url[i+2]
        break

if i==len(url):
    response = "url supplied is not github"

try:
    git = Github().get_user(user).get_repo(repo)
except UnknownObjectException:
    git = "repository does not exist. Please check link supplied"
except RateLimitExceededException:
    git = "You have reached your github rate limit. Try after an hour."
except Exception as e:
    git = "Please contact the developer for error: %s" % e

def get_required_response(config_file):      
    try:
        return yaml.safe_load(git.get_file_contents(config_file).content.decode(git.get_contents(config_file).encoding))
    except UnknownObjectException as e:
        return "The file requested was not found."
    except Exception as e:
        return "Please contact the developer for error: %s" % e



@app.route("/v1/<config_file>")
def hello(config_file):
    if isinstance(git, basestring):
        return git
    else:
        return jsonify(get_required_response(config_file))

if __name__ == "__main__":
    app.config["url"] = sys.argv[1]
    app.run(debug=True,host='0.0.0.0')
