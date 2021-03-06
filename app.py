"""Assignment - 1 CMPE 273 Spring 17"""
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

#Get user and Repo
for i in range(len(url)):
    if "github" in url[i]:
        user = url[i+1]
        repo = url[i+2]
        break

#state error if url is not a github repo
if i==len(url):
    git = "url supplied is not github"

"""This block creates a connection to the required github repository and handles errors on bad connection.
    The code was taken out of the function as the repository to be connected to is supplied when docker
    container is made. The function will only need to keep pulling the latest files from this repository.
"""
try:
    git = Github().get_user(user).get_repo(repo)
except UnknownObjectException:
    git = "repository does not exist. Please check link supplied"
except RateLimitExceededException:
    git = "You have reached your github rate limit. Try after an hour."
except Exception as e:
    git = "Please contact the developer for error: %s" % e


"""This function will get the latest version of the required config_file from the connected repository"""
def get_required_response(config_file):      
    try:
        return git.get_file_contents(config_file).content.decode(git.get_contents(config_file).encoding)
    except UnknownObjectException as e:
        filename=config_file.split(".")[0]
        extn=config_file.split(".")[1]
        try:
            if extn=="json":
                return jsonify(yaml.safe_load(git.get_file_contents(filename+".yml").content.decode(git.get_contents(filename+".yml").encoding)))
            elif extn=="yml":
                response = yaml.safe_dump(json.loads(git.get_file_contents(filename+".json").content.decode(git.get_contents(filename+".json").encoding)))
                response = response[1:len(response)-2]
                return response
        except Exception as e:
            return "File not found %s" % e
    except RateLimitExceededException:
        return "You have reached your github rate limit. Try after an hour"
    except Exception as e:
        return "Please contact the developer for error: %s" % e



@app.route("/v1/<config_file>")
def controller(config_file):
    #check if connection to github errored out
    if isinstance(git, basestring):
        return git
    else:
        return get_required_response(config_file)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0')
