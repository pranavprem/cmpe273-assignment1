from flask import Flask
from flask import jsonify
from github import Github
from github import UnknownObjectException
from github import RateLimitExceededException
import sys
import yaml
import json


app = Flask(__name__)
#print sys.argv[1]

url=sys.argv[1].split("/")
set_response_flag=False
config_file="dev-config"

#print url

for i in range(len(url)):
    if "github" in url[i]:
        user=url[i+1]
        repo=url[i+2]
        break

if(i==len(url)):
    response = "url supplied is not github"
else:
    #print user,repo
    try:
        git=Github().get_user(user).get_repo(repo)
    except UnknownObjectException:
        response = "repository does not exist. Please check link supplied"
        set_response_flag=True
    except RateLimitExceededException:
        print "reached here"
        if set_response_flag==False:
            response = "You have reached your github rate limit. Try after an hour."
            set_response_flag=True
    except Exception as e:
        if set_response_flag==False:
            response ="Please contact the developer for error: %s" % e
            set_response_flag=True

    try:
        if set_response_flag==False:
            response=yaml.safe_load(git.get_file_contents(config_file+".yml").content.decode(git.get_contents(config_file+".yml").encoding))
            set_response_flag=True
    except UnknownObjectException as e:
        try:
            if set_response_flag==False:
                response=json.loads(git.get_file_contents(config_file+".json").content.decode(git.get_contents(config_file+".json").encoding))
                set_response_flag=True
        except UnknownObjectException:
            if set_response_flag==False:
                response="The file requested was not found as json or yml. Please do not use file extension in file name"
                set_response_flag=True
    except Exception as e:
        if set_response_flag==False:
            response ="Please contact the developer for error: %s" % e
            set_response_flag=True

#print response




@app.route("/")
def hello():
    return jsonify(response)

if __name__ == "__main__":
    app.config["url"] = sys.argv[1]
    app.run(debug=True,host='0.0.0.0')
