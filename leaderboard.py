
import requests
import requests_cache
import time
import random
import logging
import base64
import re
import json
import urllib.parse
import argparse
from tqdm import tqdm
import traceback

logging.basicConfig(level=logging.ERROR)

# initialize requests-cache
requests_cache.install_cache('github_cache', expire_after=18000)  # cache expires after 5 hours

def fetch_data(url, headers, cache):
    try:
        if url in cache:
            headers['If-None-Match'] = cache[url].get('etag')

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            cache[url] = {
                'etag': response.headers.get('ETag'),
                'data': response.json()
            }
            return response.json()
        elif response.status_code == 304:
            return cache[url].get('data', None) if url in cache else None
        elif response.status_code == 401:
            raise ValueError("Error: gh_personal_access_token is expired or invalid. Please provide a valid GitHub Personal Access Token.")
        else:
            logging.error(f"Failed to fetch data from {url}: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to {url} failed: {e}")
        traceback.print_exc()
        return None
    
def fetch_status_code(url, headers, cache):
    try:
        # Check if the URL is in cache and an ETag is available
        if url in cache:
            #print(f"url({url} is in cache({cache[url].get('status_code', None)}))")
            return cache[url].get('status_code', None)
        else:
            response = requests.get(url, headers=headers)
            cache[url] = {
                'etag': response.headers.get('ETag'),
                'status_code': response.status_code
            }
            #print(f"url({url} is NOT in cache but status code is ({response.status_code})")
            return response.status_code

    except requests.exceptions.RequestException as e:
        logging.error(f"Request to {url} failed: {e}")
        traceback.print_exc()
        return None




def process_repository(repo_full_name, headers, cache):
    try:
        owner, repo_name = repo_full_name.split('/')[-2:]
        hostname = urllib.parse.urlparse(repo_full_name).hostname
        api_url_prefix = f"https://api.github.com/repos/{owner}/{repo_name}" if hostname == "github.com" else f"https://{hostname}/api/v3/repos/{owner}/{repo_name}"

        # get file list of repository root
        root_contents_url = f"{api_url_prefix}/contents"
        root_contents = fetch_data(root_contents_url, headers, cache)
        if root_contents is None:
            logging.error(f"Failed to fetch root contents for {repo_full_name}")
            return {'repo_full_name': repo_full_name}
        files = [file['name'] for file in root_contents if 'name' in file]

        # get file list of .github
        if ('.github' in files):
            github_contents_url = f"{api_url_prefix}/contents/.github"
            github_contents = fetch_data(github_contents_url, headers, cache)
            if github_contents is not None:
                files.extend([file['name'] for file in github_contents if 'name' in file])

        logging.debug(f"--- PROCESS REPOSITORY: {repo_full_name} ---")
        logging.debug(f"Files found under repo root /: {files}")

        # special check for README contents, or if doesn't meet criteria then check for PR/issues
        readme_check = '❌'
        docs_link_check = '❌'
        if ('README.md' in files):
            readme_url = f"{api_url_prefix}/contents/README.md"
            readme_response = fetch_data(readme_url, headers, cache)
            readme = base64.b64decode(readme_response['content']).decode() if readme_response else ""
            readme_required_sections = ["Features", "Contents", "Quick Start", "Changelog", "Frequently Asked Questions (FAQ)", "Contributing", "License", "Support"]
            readme_minimum_required_sections = [ "Contributing", "License", "Support" ]
            readme_sections = re.findall(r'^#+\s*(.*)$', readme, re.MULTILINE)
            if all(section in readme_sections for section in readme_required_sections):
                readme_check = '✅'
            elif len(readme_sections) > 0:
                readme_check = '☑️'
            else:
                readme_check = check_issue_pr(hostname, owner, repo_name, 'README.md', headers, cache)
            
            docs_link_check = '✅' if re.search(r'\[.*?\b(?:Docs|Documentation|Guide|Tutorial|Manual|Instructions|Handbook|Reference|User Guide|Knowledge Base|Quick Start)\b.*?\]\([^)]*\)', readme, re.IGNORECASE) else '❌'
            logging.debug("Readme contents: {readme}")     

        # Check if Dependabot Vulnerability Alerts are enabled
        vulnerability_alerts_url = f"{api_url_prefix}/vulnerability-alerts"
        vulnerability_alerts_status_code = fetch_status_code(vulnerability_alerts_url, headers, cache)  #requests.get(vulnerability_alerts_url, headers=headers)
        dependabot_alerts_enabled = '✅' if vulnerability_alerts_status_code == 204 else '❌'

        # Check if GitHub Code Scanning is enabled
        code_scanning_url = f"{api_url_prefix}/code-scanning/alerts"
        code_scanning_url_status_code = fetch_status_code(code_scanning_url, headers, cache)  #requests.get(vulnerability_alerts_url, headers=headers)
        code_scanning_enabled = '✅' if code_scanning_url_status_code == 200 else '❌'

        # Check if GitHub Secret Scanning is enabled
        secret_scanning_url = f"{api_url_prefix}/secret-scanning/alerts"
        secret_scanning_url_status_code = fetch_status_code(secret_scanning_url, headers, cache)  #requests.get(vulnerability_alerts_url, headers=headers)
        secret_scanning_enabled = '✅' if secret_scanning_url_status_code == 200 else '❌'

        results = {
            'repo_full_name': repo_full_name,
            'license': '✅' if 'LICENSE' in files or 'LICENSE.txt' in files else (check_issue_pr(hostname, owner, repo_name, 'LICENSE', headers, cache) or check_issue_pr(hostname, owner, repo_name, 'LICENSE.txt', headers, cache)),
            'readme_check': readme_check,
            'contributing_guide': '✅' if 'CONTRIBUTING.md' in files else check_issue_pr(hostname, owner, repo_name, 'CONTRIBUTING.md', headers, cache),
            'code_of_conduct': '✅' if 'CODE_OF_CONDUCT.md' in files else check_issue_pr(hostname, owner, repo_name, 'CODE_OF_CONDUCT.md', headers, cache),
            'issue_templates': '✅' if 'ISSUE_TEMPLATE' in files and 'ISSUE_TEMPLATE' in files else (check_issue_pr(hostname, owner, repo_name, 'ISSUE_TEMPLATE', headers, cache) and check_issue_pr(hostname, owner, repo_name, 'ISSUE_TEMPLATE', headers, cache)),
            'pr_template': '✅' if 'PULL_REQUEST_TEMPLATE.md' in files else check_issue_pr(hostname, owner, repo_name, 'PULL_REQUEST_TEMPLATE.md', headers, cache),
            'change_log': '✅' if 'CHANGELOG.md' in files else check_issue_pr(hostname, owner, repo_name, 'CHANGELOG.md', headers, cache),
            'docs_link_check': docs_link_check,
            'security_scanning_dependabot': dependabot_alerts_enabled,
            'security_scanning_code_scanning': code_scanning_enabled,
            'security_scanning_secrets': secret_scanning_enabled,
            'detect_secrets_check': '✅' if '.secrets.baseline' in files else check_issue_pr(hostname, owner, repo_name, '.secrets.baseline', headers, cache),
            'governance_check': '✅' if 'GOVERNANCE.md' in files else check_issue_pr(hostname, owner, repo_name, 'GOVERNANCE.md', headers, cache)
        }

        return results

    except Exception as e:
        logging.error(f"Error processing repository {repo_full_name}: {e}")
        traceback.print_exc()
        return {'repo_full_name': repo_full_name}

def check_issue_pr(hostname, owner, repo_name, file_name, headers, cache):
    api_url_prefix = f"https://api.github.com/repos/{owner}/{repo_name}" if hostname == "github.com" else f"https://{hostname}/api/v3/repos/{owner}/{repo_name}"

    issues_url = f"{api_url_prefix}/issues"
    pulls_url = f"{api_url_prefix}/pulls"

    issues = fetch_data(issues_url, headers, cache)
    pulls = fetch_data(pulls_url, headers, cache)

    issue_condition = False
    pull_request_condition = False

    if issues is not None:
        issue_condition = any(file_name in issue['title'] for issue in issues)

    if pulls is not None:
        for pull in pulls:
            pull_files_url = pull['url'] + "/files"
            pull_files = fetch_data(pull_files_url, headers, cache)
            if pull_files is not None and any(file_name in file['filename'] for file in pull_files):
                pull_request_condition = True
                break

    return '🅿️' if pull_request_condition else ('ℹ️' if issue_condition else '❌')




# load configuration from external JSON file
# accept configuration file path from command-line argument
parser = argparse.ArgumentParser(description="SLIM Best Practices Leaderboard Script")
parser.add_argument("config_path", help="Path to the JSON configuration file")
args = parser.parse_args()

# load configuration from provided file path
with open(args.config_path, "r") as file:
    config = json.load(file)

auth_token = config["gh_personal_access_token"]

if not auth_token:
    raise ValueError("Error: gh_personal_access_token in the configuration file is empty. Please provide a valid GitHub Personal Access Token.")

# make a test request to the GitHub API to check if the token is valid
headers = {"Authorization": f"token {auth_token}"}

# response = requests.get("https://api.github.com/user", headers=headers) or requests.get("https://api.github.com/user", headers=headers)
# if response.status_code == 401:
#     raise ValueError("Error: gh_personal_access_token is expired or invalid. Please provide a valid GitHub Personal Access Token.")

headers = {'Authorization': f'token {auth_token}'}
cache = {}  # dictionary to store ETag values
repos_list = []

# iterate over targets and fetch repositories
for target in config["targets"]:
    base_url = target['name'].split('/')[2]

    if target["type"] == "repository":
        repo_name = "/".join(target['name'].split('/')[-2:])
        repos_list.append(f"https://{base_url}/{repo_name}")

    elif target["type"] == "organization":
        org_name = target['name'].split('/')[-1]
        api_url = "api.github.com" if base_url == "github.com" else base_url
        org_url = f"https://{api_url}/orgs/{org_name}/repos?per_page=100"

        while org_url:
            response = requests.get(org_url, headers=headers)
            if response.status_code == 401:
                raise ValueError("Error: gh_personal_access_token is expired or invalid. Please provide a valid GitHub Personal Access Token.")
            org_repos = response.json()

            if isinstance(org_repos, list) and all(isinstance(repo, dict) for repo in org_repos):
                for repo in org_repos:
                    if (repo['archived'] or repo['disabled']): # ignore archived and disabled repositories
                        logging.warning(f"Ignoring archived or disabled repository [{ repo_name }] in org ({ org_url })")
                        continue
                    else:
                        repo_name = repo.get('name')
                        if repo_name:
                            repos_list.append(f"https://{base_url}/{org_name}/{repo_name}")
            else:
                logging.error(f"Invalid response format for organization repositories: {org_repos}")

            # check for the next page in pagination
            org_url = None
            link_header = response.headers.get('Link')
            if link_header:
                match = re.search(r'<(https://\..+?/orgs/.+?/repos\?page=\d+)>; rel="next"', link_header)
                if match:
                    org_url = match.group(1)

table_header = "| Project | Repository | LICENSE | [README](https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/) | [Contributing Guide](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/) | [Code of Conduct](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/) | [Issue Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/) | [PR Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/change-request-templates/) | [Change Log](https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/) | [Additional Docs](https://nasa-ammos.github.io/slim/docs/guides/documentation/documentation-hosts/) | [GitHub Security: Vulnerability Alerts](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/) | [GitHub Security: Code Alerts](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security) | [GitHub Security: Secrets Alerts](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security) | [Secrets Detection](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/secrets-detection/) | [Governance Model](https://nasa-ammos.github.io/slim/docs/guides/governance/governance-model/) |\n"
table_header += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
rows = []

infused_count = pr_count = issue_count = total_count = 0
for repo in tqdm(repos_list, desc="Scanning Repository", unit="repo"):
    repo_data = process_repository(repo, headers, cache)

    if repo_data:
        owner, repo_name = repo_data['repo_full_name'].split('/')[-2:]
        hostname = urllib.parse.urlparse(repo_data['repo_full_name']).hostname
        repo_url = f"https://{hostname}/{owner}/{repo_name}"
        row = (
            f"| [{owner}](https://{hostname}/{owner}) "
            f"| [{repo_name}]({repo_url}) "
            f"| {repo_data.get('license', '❌')} "
            f"| {repo_data.get('readme_check', '❌')} "
            f"| {repo_data.get('contributing_guide', '❌')} "
            f"| {repo_data.get('code_of_conduct', '❌')} "
            f"| {repo_data.get('issue_templates', '❌')} "
            f"| {repo_data.get('pr_template', '❌')} "
            f"| {repo_data.get('change_log', '❌')} "
            f"| {repo_data.get('docs_link_check', '❌')} "
            f"| {repo_data.get('security_scanning_dependabot', '❌')} "
            f"| {repo_data.get('security_scanning_code_scanning', '❌')} "
            f"| {repo_data.get('security_scanning_secrets', '❌')} "
            f"| {repo_data.get('detect_secrets_check', '❌')} "
            f"| {repo_data.get('governance_check', '❌')} |"
        )
        tmp_infused_count = row.count('✅') + row.count('☑️')
        infused_count += row.count('✅') + row.count('☑️')
        pr_count += row.count('🅿️') 
        issue_count += row.count('ℹ️')
        total_count += 7
        rows.append((tmp_infused_count, row))
        logging.info(row)

# sort rows by the number of '✅' values and add them to the table
rows.sort(reverse=True)
table = table_header + '\n'.join(row for _, row in rows)
report = f"\n#REPORT:\n- Infused Count: {infused_count}\n- Pull Requests Count: {pr_count}\n- Issue Count: {issue_count}\n- Total Count: {total_count}"

markdown_toc = """
## Table of Contents
- [Leaderboard Table](#leaderboard-table) - a ranked listing of Unity repositories in order of how many best practice / compliance checks have been met.
- [Summary Report](#summary-report) - a summarization report of total checks run, number of infused best practices detected, number of proposed detecetd. etc.
- [Repository Check Explanation](#repository-check-explanation) - detailed explanations for the logic used to generate an ✅,  ☑️, ℹ️, 🅿️, or ❌ for each check.

"""

markdown_table = f"""
## Leaderboard Table
{table}

"""

markdown_report = f"""
## Summary Report 

The below table summarizes the effect of generating the above leaderboard table. Here's an explanation of each summarization statistic: 
- Infused Count: the total number of best practices that have been detected infused into code repositories
- Proposed PR Count: the total number of best practices that are currently in proposal state as pull-requests to code repositories
- Proposed Issues Count: the total number of best practices that are currently in proposal state as issue tickets to code repositories
- Total Checks Run Count: the total number of best practice checks that have been run against the total number of repositories evaluated

| Infused Count (✅, ☑️) | Proposed PR Count (🅿️) | Proposed Issues Count (ℹ️) | Total Checks Run Count |
| ---------------------- | --------------------- | ------------------------- | --------------------- |
| {infused_count}        | {pr_count}            | {issue_count}             | {total_count}        |

"""

markdown_directions = """
## Repository Check Explanation 

Each check against a repository will result in one of the following statuses:
- ✅: The check passed, indicating that the repository meets the requirement.
- 🅿️: Indicates a best practice is currently in proposal state as a pull-request to the repository.
- ℹ️: Indicates a best practice is currently in proposal state as an issue ticket to the repository.

### 1. License:
- The repository must contain a file named either `LICENSE` or `LICENSE.txt`.
- ✅ The check will pass with a green check mark if either of these files is present.
- 🅿️ If a pull-request is proposed to add the `LICENSE` or `LICENSE.txt`.
- ℹ️ If an issue is opened to suggest adding the `LICENSE` or `LICENSE.txt`.

### 2. README Sections:
- The README must contain sections with the following titles: 
  - "Features"
  - "Contents"
  - "Quick Start"
  - "Changelog"
  - "Frequently Asked Questions (FAQ)"
  - "Contributing"
  - "License"
  - "Support"
- ✅ If all these sections are present, the check will pass with a green check mark.
- ☑️ If the README file exists and has at least one section header.
- 🅿️ If a pull-request is proposed to add missing sections.
- ℹ️ If an issue is opened to suggest adding missing sections.

### 3. Contributing Guide:
- The repository must contain a file named `CONTRIBUTING.md`.
- ✅ The check will pass with a green check mark if this file is present.
- 🅿️ If a pull-request is proposed to add the `CONTRIBUTING.md`.
- ℹ️ If an issue is opened to suggest adding the `CONTRIBUTING.md`.

### 4. Code of Conduct:
- The repository must contain a file named `CODE_OF_CONDUCT.md`.
- ✅ The check will pass with a green check mark if this file is present.
- 🅿️ If a pull-request is proposed to add the `CODE_OF_CONDUCT.md`.
- ℹ️ If an issue is opened to suggest adding the `CODE_OF_CONDUCT.md`.

### 5. Issue Templates:
- The repository must have the following issue templates:
  - `bug_report.md`: Template for bug reports.
  - `feature_request.md`: Template for feature requests.
- ✅ The check will pass with a green check mark if both templates are present.
- 🅿️ If a pull-request is proposed to add missing templates.
- ℹ️ If an issue is opened to suggest adding missing templates.

### 6. PR Templates:
- The repository must have a pull request (PR) template.
- ✅ The check will pass with a green check mark if the PR template is present.
- 🅿️ If a pull-request is proposed to add a PR template.
- ℹ️ If an issue is opened to suggest adding a PR template.

### 7. Change Log:
- The repository must contain a file named `CHANGELOG.md`.
- ✅ The check will pass with a green check mark if this file is present.
- 🅿️ If a pull-request is proposed to add the `CHANGELOG.md`.
- ℹ️ If an issue is opened to suggest adding the `CHANGELOG.md`.

### 8. Additional Docs:
- The README must contain a link to additional documentation, with a link label containing terms like "Docs", "Documentation", "Guide", "Tutorial", "Manual", "Instructions", "Handbook", "Reference", "User Guide", "Knowledge Base", or "Quick Start". Ex: "Unity-SPS Docs", "docs", or "Unity Documentation".
- ✅ The check will pass with a green check mark if this link is present.
- 🅿️ If a pull-request is proposed to add the link.
- ℹ️ If an issue is opened to suggest adding the link.

"""

# either write to file or print based on config
if "output" in config:
    with open(config["output"], "w") as file:
        file.write(markdown_toc)
        file.write(markdown_table)
        file.write(markdown_report)
        file.write(markdown_directions)
else:
    print("\n")
    print(markdown_table)
