
import requests
import time
import random
import logging
import base64
import re
import json
import urllib.parse
import argparse

logging.basicConfig(level=logging.DEBUG)

# Load configuration from external JSON file
# Accept configuration file path from command-line argument
parser = argparse.ArgumentParser(description="SLIM Best Practices Leaderboard Script")
parser.add_argument("config_path", help="Path to the JSON configuration file")
args = parser.parse_args()

# Load configuration from provided file path
with open(args.config_path, "r") as file:
    config = json.load(file)

auth_token = config["gh_personal_access_token"]
if not auth_token:
    raise ValueError("Error: gh_personal_access_token in the configuration file is empty. Please provide a valid GitHub Personal Access Token.")

headers = {'Authorization': f'token {auth_token}'}
repos_list = []

# Iterate over targets and fetch repositories
for target in config["targets"]:
    base_url = target['name'].split('/')[2]

    if target["type"] == "repository":
        repo_name = "/".join(target['name'].split('/')[-2:])
        repos_list.append(f"https://{base_url}/{repo_name}")




    elif target["type"] == "organization":
        org_name = target['name'].split('/')[-1]
        api_url = "api.github.com" if base_url == "github.com" else base_url # to support compatibility between github.com and github enterprise
        org_url = f"https://{api_url}/orgs/{org_name}/repos?per_page=100"
        while org_url:
            response = requests.get(org_url, headers=headers)
            org_repos = response.json()

            # Check for the next page in pagination
            org_url = None
            link_header = response.headers.get('Link')
            if link_header:
                match = re.search(r'<(https://\..+?/orgs/.+?/repos\?page=\d+)>; rel="next"', link_header)
                if match:
                    org_url = match.group(1)

        for repo in org_repos:
            repos_list.append(f"https://{base_url}/{org_name}/{repo['name']}")
            # Check for the next page in pagination
            org_url = None
            link_header = response.headers.get('Link')
            if link_header:
                match = re.search(r'<(https://\..+?/orgs/.+?/repos\?page=\d+)>; rel="next"', link_header)
                if match:
                    org_url = match.group(1)



table_header = "| Project | Repository | [Issue Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/) | [PR Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/change-request-templates/) | [Code of Conduct](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/) | [Contributing Guide](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/) | LICENSE | [README](https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/) | [Change Log](https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/) | Link to Docs in README |\n"
table_header += "|---|---|---|---|---|---|---|---|---|---|\n"
rows = []

for repo_full_name in repos_list:
    owner, repo_name = repo_full_name.split('/')[-2:]
    hostname = urllib.parse.urlparse(repo_full_name).hostname
    repo_url = f"https://{hostname}/{owner}/{repo_name}"
    api_url_prefix = f"https://api.github.com/repos/{org_name}/{repo_name}/contents" if hostname == "github.com" else f"https://{hostname}/api/v3/repos/{owner}/{repo_name}/contents"

    issue_template_url = f"{api_url_prefix}/.github/ISSUE_TEMPLATE"
    pr_template_url = f"{api_url_prefix}/.github/PULL_REQUEST_TEMPLATE.md"
    contents_url = f"{api_url_prefix}"
    readme_url = f"{api_url_prefix}/README.md"

    jitter = random.uniform(0.5, 1.5)
    time.sleep(jitter)  # jittering

    issue_templates_response = requests.get(issue_template_url, headers=headers)
    pr_template_response = requests.get(pr_template_url, headers=headers)
    contents_response = requests.get(contents_url, headers=headers)
    readme_response = requests.get(readme_url, headers=headers)

    issue_templates = issue_templates_response.json() if issue_templates_response.status_code == 200 else []
    pr_templates = '✅' if pr_template_response.status_code == 200 else '❌'
    contents = contents_response.json() if contents_response.status_code == 200 else []
    readme = base64.b64decode(readme_response.json()['content']).decode() if readme_response.status_code == 200 else ""

    issue_template_files = [file['name'] for file in issue_templates]
    files = [file['name'] for file in contents]

    issue_templates = '✅' if 'bug_report.md' in issue_template_files and 'feature_request.md' in issue_template_files else '❌'
    code_of_conduct = '✅' if 'CODE_OF_CONDUCT.md' in files else '❌'
    contributing_guide = '✅' if 'CONTRIBUTING.md' in files else '❌'
    license = '✅' if 'LICENSE' in files or 'LICENSE.txt' in files else '❌'
    change_log = '✅' if 'CHANGELOG.md' in files else '❌'

    required_sections = ["Features", "Contents", "Quick Start", "Changelog", "Frequently Asked Questions (FAQ)", "Contributing", "License", "Support"]
    minimum_required_sections = [ "Contributing", "License", "Support" ]
    readme_sections = re.findall(r'^#+\s*(.*)$', readme, re.MULTILINE)
    if all(section in readme_sections for section in required_sections):
        readme_check = '✅'
    elif all(section in readme_sections for section in minimum_required_sections):
        readme_check = '☑️'
    else:
        readme_check = '❌'

    docs_link = '✅' if re.search(r'\[.*?\b(?:Docs|Documentation)\b.*?\]\(.*\)', readme, re.IGNORECASE) else '❌'

    row = f"| [{owner}](https://{hostname}/{owner}) | [{repo_name}]({repo_url}) | {issue_templates} | {pr_templates} | {code_of_conduct} | {contributing_guide} | {license} | {readme_check} | {change_log} | {docs_link} |"
    rows.append((row.count('✅') + row.count('☑️'), row))

    logging.info(row) # print the markdown rendering of the row

# Sort rows by the number of '✅' values and add them to the table
rows.sort(reverse=True)
table = table_header + '\n'.join(row for _, row in rows)

# Either write to file or print based on config
if "output" in config:
    with open(config["output"], "w") as file:
        file.write(table)
else:
    print("\n")
    print(table)
