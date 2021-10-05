import json
import re
import os
import urllib.request
import glob
from github import Github
import sys
from pathlib import Path
import subprocess

pat = re.compile(r"^data-processed/(.+)/\d\d\d\d-\d\d-\d\d-\1\.csv")
pat_meta = re.compile(r"^data-processed/(.+)/metadata-\1\.txt$")

token  = os.environ.get('GH_TOKEN')
print("Added token")
print(f"Token length: {len(token)}")
    
g = Github(token)
repo_name = os.environ.get('GITHUB_REPOSITORY')
repo = g.get_repo(repo_name)

print(f"Github repository: {repo_name}")
print(f"Github event name: {os.environ.get('GITHUB_EVENT_NAME')}")

event = json.load(open(os.environ.get('GITHUB_EVENT_PATH')))

pr = None
comment = ''
files_changed = []

# Fetch the  PR number from the event json
pr_num = event['pull_request']['number']
print(f"PR number: {pr_num}")

# Use the Github API to fetch the Pullrequest Object. Refer to details here: https://pygithub.readthedocs.io/en/latest/github_objects/PullRequest.html 
# pr is the Pullrequest object
pr = repo.get_pull(pr_num)

# fetch all files changed in this PR and add it to the files_changed list.
files_changed += [f for f in pr.get_files()]
    
# Split all files in `files_changed` list into valid forecasts and other files
forecasts = [file for file in files_changed if pat.match(file.filename) is not None]
metadatas = [file for file in files_changed if pat_meta.match(file.filename) is not None]
rawdatas = [file for file in files_changed if file.filename[0:8] == "data-raw"]
other_files = [file for file in files_changed if (pat.match(file.filename) is None and pat_meta.match(file.filename) is None and file not in rawdatas)]

print(forecasts)

# IF there are other fiels changed in the PR 
#TODO: If there are other files changed as well as forecast files added, then add a comment saying so. 
if len(other_files) > 0 and len(forecasts) >0:
    print(f"PR has other files changed too.")
    if pr is not None:
        pr.add_to_labels('other-files-updated')

if len(metadatas) > 0:
    print(f"PR has metata files changed.")
    if pr is not None:
        pr.add_to_labels('metadata-change')

if len(rawdatas) > 0:
    print(f"PR has raw files changed.")
    if pr is not None:
        pr.add_to_labels('added-raw-data')
# Do not require this as it is done by the PR labeler action.
if len(forecasts) > 0:
    if pr is not None:
        pr.add_to_labels('data-submission')


deleted_forecasts = False
changed_forecasts = False

# `f` is ab object of type: https://pygithub.readthedocs.io/en/latest/github_objects/File.html 
# `forecasts` is a list of `File`s that are changed in the PR.
for f in forecasts:
    # check if file is remove
    if f.status == "removed":
        deleted_forecasts = True

    # if file status is not "added" it is probably "renamed" or "changed"
    elif f.status != "added":
        changed_forecasts = True

if deleted_forecasts:
    pr.add_to_labels('forecast-deleted')
    comment += "\n Your submission seem to have deleted some forecasts. Could you provide a reason for the updation/deletion? Thank you!\n\n"

if changed_forecasts:
    pr.add_to_labels('forecast-updated')
    comment += "\n Your submission seem to have updated/renamed some forecasts. Could you provide a reason for the updation/deletion? Thank you!\n\n"