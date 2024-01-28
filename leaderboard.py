
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
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        else:
            logging.error(f"Failed to fetch data from {url}: {response.status_code} - {response.text}")
            return None
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

        results = {
            'repo_full_name': repo_full_name,
            'issue_templates': '✅' if 'ISSUE_TEMPLATE' in files and 'ISSUE_TEMPLATE' in files else (check_issue_pr(hostname, owner, repo_name, 'ISSUE_TEMPLATE', headers, cache) and check_issue_pr(hostname, owner, repo_name, 'ISSUE_TEMPLATE', headers, cache)),
            'pr_template': '✅' if 'PULL_REQUEST_TEMPLATE.md' in files else check_issue_pr(hostname, owner, repo_name, 'PULL_REQUEST_TEMPLATE.md', headers, cache),
            'code_of_conduct': '✅' if 'CODE_OF_CONDUCT.md' in files else check_issue_pr(hostname, owner, repo_name, 'CODE_OF_CONDUCT.md', headers, cache),
            'contributing_guide': '✅' if 'CONTRIBUTING.md' in files else check_issue_pr(hostname, owner, repo_name, 'CONTRIBUTING.md', headers, cache),
            'license': '✅' if 'LICENSE' in files or 'LICENSE.txt' in files else (check_issue_pr(hostname, owner, repo_name, 'LICENSE', headers, cache) or check_issue_pr(hostname, owner, repo_name, 'LICENSE.txt', headers, cache)),
            'change_log': '✅' if 'CHANGELOG.md' in files else check_issue_pr(hostname, owner, repo_name, 'CHANGELOG.md', headers, cache),
        }

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
            elif all(section in readme_sections for section in readme_minimum_required_sections):
                readme_check = '☑️'
            else:
                readme_check = check_issue_pr(hostname, owner, repo_name, 'README.md', headers, cache)
            
            docs_link_check = '✅' if re.search(r'\[.*?\b(?:Docs|Documentation)\b.*?\]\(.*\)', readme, re.IGNORECASE) else '❌'
                

        results['readme_check'] = readme_check   
        results['docs_link_check'] = docs_link_check     

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
response = requests.get("https://api.github.com/user", headers=headers)
if response.status_code == 401:
    raise ValueError("Error: gh_personal_access_token is expired or invalid. Please provide a valid GitHub Personal Access Token.")

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

table_header = "| Project | Repository | [Issue Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/) | [PR Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/change-request-templates/) | [Code of Conduct](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/) | [Contributing Guide](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/) | LICENSE | [README](https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/) | [Change Log](https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/) | Link to Docs in README |\n"
table_header += "|---|---|---|---|---|---|---|---|---|---|\n"
rows = []

infused_count = pr_count = issue_count = total_count = 0
with ThreadPoolExecutor(max_workers=1) as executor: # keep max_workers=1 because of bug where multithreading doesn't work with requests-cache well
    future_to_repo = {executor.submit(process_repository, repo, headers, cache): repo for repo in repos_list}
   

    for future in tqdm(as_completed(future_to_repo), total=len(repos_list), desc="Processing Repositories"):
        repo_data = future.result()

        if repo_data:
            owner, repo_name = repo_data['repo_full_name'].split('/')[-2:]
            hostname = urllib.parse.urlparse(repo_data['repo_full_name']).hostname
            repo_url = f"https://{hostname}/{owner}/{repo_name}"
            row = f"| [{owner}](https://{hostname}/{owner}) | [{repo_name}]({repo_url}) | {repo_data.get('issue_templates', '❌')} | {repo_data.get('pr_template', '❌')} | {repo_data.get('code_of_conduct', '❌')} | {repo_data.get('contributing_guide', '❌')} | {repo_data.get('license', '❌')} | {repo_data.get('readme_check', '❌')} | {repo_data.get('changelog_check', '❌')} | {repo_data.get('docs_link_check', '❌')}"
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

# either write to file or print based on config
if "output" in config:
    with open(config["output"], "w") as file:
        file.write(table)
        file.write(report)
else:
    print("\n")
    print(table)
