from flask import Flask
from flask import jsonify
from github import Github
from github import UnknownObjectException
import yaml

url="https://github.com/sithu/assignment1-config-example".split("/")

config_file="dev-config"

for i in range(len(url)):
    if "github" in url[i]:
        user=url[i+1]
        repo=url[i+2]
        break


print user,repo
lastModified=open("last_commit.txt").read()


app = Flask(__name__)

git=Github().get_user(user).get_repo(repo)
try:
    response=yaml.safe_load(git.get_file_contents(config_file+".yml").content.decode(git.get_contents(config_file+".yml").encoding))
except UnknownObjectException as e:
    try:
        response=yaml.safe_load(git.get_file_contents(config_file+".json").content.decode(git.get_contents(config_file+".json").encoding))
    except UnknownObjectException:
        response="The file requested was not found as json or yml. Please do not use file extension in file name"
except Exception as e:
    print e

print response


@app.route("/")
def hello():
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
