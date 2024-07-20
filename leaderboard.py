
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

logging.basicConfig(level=logging.INFO)

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
    
def fetch_status_code(url, headers):
    """Fetch the status code for a given URL."""
    try:
        logging.debug(f"Fetching URL {url}")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            logging.debug(f"URL {url} fetched successfully with status 200")
        else:
            logging.debug(f"URL {url} returned status {response.status_code}")
        return response.status_code
    except requests.exceptions.RequestException as e:
        logging.error(f"Request to {url} failed: {e}")
        return None

def fetch_status_codes(rest_api_url, endpoints, headers):
    """Fetch status codes for multiple URLs in parallel with retries and exponential backoff."""
    results = {}
    urls = [f"{rest_api_url}{endpoint}" for endpoint in endpoints]
    max_workers = min(10, len(urls))  # Use a reasonable number of workers
    logging.debug(f"Starting to fetch status codes for {len(urls)} URLs with {max_workers} workers.")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(fetch_status_code, url, headers): url
            for url in urls
        }
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            endpoint = url.replace(rest_api_url, "")
            try:
                result = future.result()
                results[endpoint] = result
                logging.debug(f"Received result for URL {url}: {result}")
            except Exception as exc:
                results[endpoint] = None
                logging.error(f"{url} generated an exception: {exc}")
    logging.debug("Completed fetching all URLs.")
    return results

def run_graphql_query(hostname, headers, query):
    api_url_prefix = f"https://api.github.com/graphql" if hostname == "github.com" else f"https://{hostname}/api/graphql"
    request = requests.post(api_url_prefix, json={'query': query}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("GraphQL query failed to run by returning code of {}. {}".format(request.status_code, query))

def check_files_existence(owner, repo_name, api_url, headers):
    """Check if specific files exist in the repository by path names."""
    query = """
    query CheckFilesExistence($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        readme: object(expression: "HEAD:README.md") {
          ... on Blob {
            text
          }
        }
        license: object(expression: "HEAD:LICENSE") {
          ... on Blob {
            id
          }
        }
        licenseTxt: object(expression: "HEAD:LICENSE.txt") {
        ... on Blob {
            id
        }
        }
        contributing: object(expression: "HEAD:CONTRIBUTING.md") {
          ... on Blob {
            id
          }
        }
        code_of_conduct: object(expression: "HEAD:CODE_OF_CONDUCT.md") {
          ... on Blob {
            id
          }
        }
        issue_templates: object(expression: "HEAD:.github/ISSUE_TEMPLATE") {
          ... on Blob {
            id
          }
        }
        pull_request_template: object(expression: "HEAD:.github/PULL_REQUEST_TEMPLATE.md") {
          ... on Blob {
            id
          }
        }
        changelog: object(expression: "HEAD:CHANGELOG.md") {
          ... on Blob {
            id
          }
        }
        secrets_baseline: object(expression: "HEAD:.secrets.baseline") {
          ... on Blob {
            id
          }
        }
        governance: object(expression: "HEAD:GOVERNANCE.md") {
          ... on Blob {
            id
          }
        }
        issues(first: 100) {
          nodes {
            title
          }
        }
        pullRequests(first: 100) {
          nodes {
            title
            files(first: 100) {
              nodes {
                path
              }
            }
          }
        }
      }
    }
    """
    variables = {
        'owner': owner,
        'name': repo_name
    }
    response = requests.post(
        api_url,
        json={'query': query, 'variables': variables},
        headers=headers
    )

    def generate_check_mark(file_name, file_status, issues, prs):
        if file_status is not None: 
            return 'PASS'
        elif any(file_name in issue for issue in issues):
            return 'TICKET'
        elif any(file_name in pr['title'] or any(file_name in file for file in pr['files']) for pr in prs):
            return 'PR'
        else:
            return 'FAIL'

    if response.status_code == 200:
        result = response.json()
        issues = [issue['title'] for issue in result['data']['repository']['issues']['nodes']]
        pull_requests = [{
            'title': pr['title'],
            'files': [file['path'] for file in pr['files']['nodes']]
        } for pr in result['data']['repository']['pullRequests']['nodes']]

        # README in-depth checks
        readme_text = result['data']['repository']['readme']['text'] if result['data']['repository']['readme'] else ""
        readme_required_sections = ["Features", "Contents", "Quick Start", "Changelog", "Frequently Asked Questions (FAQ)", "Contributing", "License", "Support"]
        readme_sections = re.findall(r'^#+\s*(.*)$', readme_text, re.MULTILINE)
        if all(section in readme_sections for section in readme_required_sections):
            readme_check = 'PASS'
        elif len(readme_sections) > 0:
            readme_check = 'WARN'
        else:
            readme_check = generate_check_mark('README.md', False, issues, pull_requests)

        docs_link_check = 'PASS' if re.search(r'\[.*?\b(?:Docs|Documentation|Guide|Tutorial|Manual|Instructions|Handbook|Reference|User Guide|Knowledge Base|Quick Start)\b.*?\]\([^)]*\)', readme_text, re.IGNORECASE) else 'FAIL'


        checks = {
            'owner': owner,
            'repo': repo_name,
            'readme': readme_check,
            'license': generate_check_mark('LICENSE', result['data']['repository']['license'] or result['data']['repository']['licenseTxt'], issues, pull_requests),
            'contributing': generate_check_mark('CONTRIBUTING.md', result['data']['repository']['contributing'], issues, pull_requests),
            'code_of_conduct': generate_check_mark('CODE_OF_CONDUCT.md', result['data']['repository']['code_of_conduct'], issues, pull_requests),
            'issue_templates': generate_check_mark('.github/ISSUE_TEMPLATE', result['data']['repository']['issue_templates'], issues, pull_requests),
            'pull_request_template': generate_check_mark('PULL_REQUEST_TEMPLATE.md', result['data']['repository']['pull_request_template'], issues, pull_requests),
            'changelog': generate_check_mark('CHANGELOG.md', result['data']['repository']['changelog'], issues, pull_requests),
            'docs_link_check': docs_link_check,
            'secrets_baseline': generate_check_mark('.secrets.baseline', result['data']['repository']['secrets_baseline'], issues, pull_requests),
            'governance': generate_check_mark('GOVERNANCE.md', result['data']['repository']['governance'], issues, pull_requests)
        }
        return checks
    else:
        logging.error(f"Failed to check file existence for {owner}/{repo_name} at {api_url}: {response.status_code} - {response.text}")
        return None

def process_repository(repo_full_name, headers):
    try:
        owner, repo_name = repo_full_name.split('/')[-2:]
        hostname = urllib.parse.urlparse(repo_full_name).hostname
        graphql_api_url = f"https://api.github.com/graphql" if hostname == "github.com" else f"https://{hostname}/api/graphql"
        rest_api_url = f"https://api.github.com/repos/{owner}/{repo_name}" if hostname == "github.com" else f"https://{hostname}/api/v3/repos/{owner}/{repo_name}"

        checks = check_files_existence(owner, repo_name, graphql_api_url, headers)
        status_codes = fetch_status_codes(rest_api_url,
            ["/vulnerability-alerts",
             "/code-scanning/alerts",
             "/secret-scanning/alerts"],
             headers
        )
        #print(status_codes)
        status_checks = {}
        status_checks['/vulnerability-alerts'] = 'PASS' if status_codes['/vulnerability-alerts'] == 204 else 'FAIL'
        status_checks['/code-scanning/alerts'] = 'PASS' if status_codes['/code-scanning/alerts'] == 200 else 'FAIL'
        status_checks['/secret-scanning/alerts'] = 'PASS' if status_codes['/secret-scanning/alerts'] == 200 else 'FAIL'
        
        # Safely merge checks
        result = {**checks, **status_checks} if checks else status_checks

        return result

    except Exception as e:
        logging.error(f"Error processing repository {repo_full_name}: {e}")
        traceback.print_exc()
        return {'repo_full_name': repo_full_name}


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

response = requests.get("https://api.github.com/user", headers=headers) or requests.get("https://api.github.com/user", headers=headers)
if response.status_code == 401:
    raise ValueError("Error: gh_personal_access_token is expired or invalid. Please provide a valid GitHub Personal Access Token.")

#cache = {}  # dictionary to store ETag values
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

#table_header = "| Project | Repository | LICENSE | [README](https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/) | [Contributing Guide](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/) | [Code of Conduct](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/) | [Issue Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/) | [PR Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/change-request-templates/) | [Change Log](https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/) | [Additional Docs](https://nasa-ammos.github.io/slim/docs/guides/documentation/documentation-hosts/) | [GitHub Security: Vulnerability Alerts](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/) | [GitHub Security: Code Alerts](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security) | [GitHub Security: Secrets Alerts](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security) | [Secrets Detection](https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/secrets-detection/) | [Governance Model](https://nasa-ammos.github.io/slim/docs/guides/governance/governance-model/) |\n"
#table_header += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
rows = []

infused_count = pr_count = issue_count = total_count = 0
for repo in tqdm(repos_list, desc="Scanning Repository", unit="repo"):
    rows.append(process_repository2(repo, headers))
    # print(repo_data)

console = Console()
# Create the root of the tree
tree = Tree("Repository Information")

def colorize_status(status):
    """Apply color based on status."""
    if status == 'PASS':
        return f"[green]{status}[/green]"
    elif status == 'FAIL':
        return f"[red]{status}[/red]"
    elif status == 'WARN':
        return f"[yellow]{status}[/yellow]"
    elif status == 'ISSUE':
        return f"[blue]{status}[/blue]"
    elif status == 'PR':
        return f"[blue]{status}[/blue]"
    else:
        return status  # No color if not one of the above

# Add branches and leaves to the tree
for row in rows:
    repo_branch = tree.add(f"[bold magenta]{row['owner']}/{row['repo']}[/bold magenta]")

    # Adding each field manually with customized labels
    repo_branch.add(f"License: {colorize_status(row['license'])}")
    repo_branch.add(f"Readme: {colorize_status(row['readme'])}")
    repo_branch.add(f"Contributing Guide: {colorize_status(row['contributing'])}")
    repo_branch.add(f"Code of Conduct: {colorize_status(row['code_of_conduct'])}")
    repo_branch.add(f"Issue Templates: {colorize_status(row['issue_templates'])}")
    repo_branch.add(f"PR Templates: {colorize_status(row['pull_request_template'])}")
    repo_branch.add(f"Changelog: {colorize_status(row['changelog'])}")
    repo_branch.add(f"Additional Documentation: {colorize_status(row['docs_link_check'])}")
    repo_branch.add(f"Secrets Detection: {colorize_status(row['secrets_baseline'])}")
    repo_branch.add(f"Governance Model: {colorize_status(row['governance'])}")

    # Alerts and scanning status with customized labels
    alerts_branch = repo_branch.add("[bold yellow]GitHub Configuration[/bold yellow]")
    alerts_branch.add(f"Vulnerability Alerts: {colorize_status(row['/vulnerability-alerts'])}")
    alerts_branch.add(f"Code Scanning Status: {colorize_status(row['/code-scanning/alerts'])}")
    alerts_branch.add(f"Secret Scanning Effectiveness: {colorize_status(row['/secret-scanning/alerts'])}")

# Print the tree to the console
console.print(tree)

# table = Table(show_header=True, header_style="bold magenta", show_lines=True, overflow="fold")

# # Define the headers
# headers = [
#     "Owner", "Repo",  "License", "Readme", "Contributing", "Code of Conduct",
#     "Issue Templates", "PR Template", "Changelog", "Additional Docs", 
#     "GitHub: Vulnerability Alerts", "GitHub: Code Alerts", "GitHub: Secrets Alerts", 
#     "Secrets Detection", "Governance"
# ]

# # Add columns to the table
# for header in headers:
#     table.add_column(header)

# # Add rows to the table
# for row in rows:
#     table.add_row(
#         row['owner'],
#         row['repo'],
#         row['license'],
#         row['readme'],
#         row['contributing'],
#         row['code_of_conduct'],
#         row['issue_templates'],
#         row['pull_request_template'],
#         row['changelog'],
#         row['docs_link_check'],
#         str(row['/vulnerability-alerts']),
#         str(row['/code-scanning/alerts']),
#         str(row['/secret-scanning/alerts']),
#         row['secrets_baseline'],
#         row['governance']
#     )

# # Print the table to the console
# console.print(table)

#     if repo_data:
#         owner, repo_name = repo_data['repo_full_name'].split('/')[-2:]
#         hostname = urllib.parse.urlparse(repo_data['repo_full_name']).hostname
#         repo_url = f"https://{hostname}/{owner}/{repo_name}"
#         row = (
#             f"| [{owner}](https://{hostname}/{owner}) "
#             f"| [{repo_name}]({repo_url}) "
#             f"| {repo_data.get('license', '❌')} "
#             f"| {repo_data.get('readme_check', '❌')} "
#             f"| {repo_data.get('contributing_guide', '❌')} "
#             f"| {repo_data.get('code_of_conduct', '❌')} "
#             f"| {repo_data.get('issue_templates', '❌')} "
#             f"| {repo_data.get('pr_template', '❌')} "
#             f"| {repo_data.get('change_log', '❌')} "
#             f"| {repo_data.get('docs_link_check', '❌')} "
#             f"| {repo_data.get('security_scanning_dependabot', '❌')} "
#             f"| {repo_data.get('security_scanning_code_scanning', '❌')} "
#             f"| {repo_data.get('security_scanning_secrets', '❌')} "
#             f"| {repo_data.get('detect_secrets_check', '❌')} "
#             f"| {repo_data.get('governance_check', '❌')} |"
#         )
#         tmp_infused_count = row.count('✅') + row.count('☑️')
#         infused_count += row.count('✅') + row.count('☑️')
#         pr_count += row.count('🅿️') 
#         issue_count += row.count('ℹ️')
#         total_count += 7
#         rows.append((tmp_infused_count, row))
#         logging.info(row)

# # sort rows by the number of '✅' values and add them to the table
# rows.sort(reverse=True)
# table = table_header + '\n'.join(row for _, row in rows)
# report = f"\n#REPORT:\n- Infused Count: {infused_count}\n- Pull Requests Count: {pr_count}\n- Issue Count: {issue_count}\n- Total Count: {total_count}"

# markdown_toc = """
# ## Table of Contents
# - [Leaderboard Table](#leaderboard-table) - a ranked listing of Unity repositories in order of how many best practice / compliance checks have been met.
# - [Summary Report](#summary-report) - a summarization report of total checks run, number of infused best practices detected, number of proposed detecetd. etc.
# - [Repository Check Explanation](#repository-check-explanation) - detailed explanations for the logic used to generate an ✅,  ☑️, ℹ️, 🅿️, or ❌ for each check.

# """

# markdown_table = f"""
# ## Leaderboard Table
# {table}

# """

# markdown_report = f"""
# ## Summary Report 

# The below table summarizes the effect of generating the above leaderboard table. Here's an explanation of each summarization statistic: 
# - Infused Count: the total number of best practices that have been detected infused into code repositories
# - Proposed PR Count: the total number of best practices that are currently in proposal state as pull-requests to code repositories
# - Proposed Issues Count: the total number of best practices that are currently in proposal state as issue tickets to code repositories
# - Total Checks Run Count: the total number of best practice checks that have been run against the total number of repositories evaluated

# | Infused Count (✅, ☑️) | Proposed PR Count (🅿️) | Proposed Issues Count (ℹ️) | Total Checks Run Count |
# | ---------------------- | --------------------- | ------------------------- | --------------------- |
# | {infused_count}        | {pr_count}            | {issue_count}             | {total_count}        |

# """

# markdown_directions = """
# ## Repository Check Explanation 

# Each check against a repository will result in one of the following statuses:
# - ✅: The check passed, indicating that the repository meets the requirement.
# - 🅿️: Indicates a best practice is currently in proposal state as a pull-request to the repository.
# - ℹ️: Indicates a best practice is currently in proposal state as an issue ticket to the repository.

# ### 1. License:
# - The repository must contain a file named either `LICENSE` or `LICENSE.txt`.
# - ✅ The check will pass with a green check mark if either of these files is present.
# - 🅿️ If a pull-request is proposed to add the `LICENSE` or `LICENSE.txt`.
# - ℹ️ If an issue is opened to suggest adding the `LICENSE` or `LICENSE.txt`.

# ### 2. README Sections:
# - The README must contain sections with the following titles: 
#   - "Features"
#   - "Contents"
#   - "Quick Start"
#   - "Changelog"
#   - "Frequently Asked Questions (FAQ)"
#   - "Contributing"
#   - "License"
#   - "Support"
# - ✅ If all these sections are present, the check will pass with a green check mark.
# - ☑️ If the README file exists and has at least one section header.
# - 🅿️ If a pull-request is proposed to add missing sections.
# - ℹ️ If an issue is opened to suggest adding missing sections.

# ### 3. Contributing Guide:
# - The repository must contain a file named `CONTRIBUTING.md`.
# - ✅ The check will pass with a green check mark if this file is present.
# - 🅿️ If a pull-request is proposed to add the `CONTRIBUTING.md`.
# - ℹ️ If an issue is opened to suggest adding the `CONTRIBUTING.md`.

# ### 4. Code of Conduct:
# - The repository must contain a file named `CODE_OF_CONDUCT.md`.
# - ✅ The check will pass with a green check mark if this file is present.
# - 🅿️ If a pull-request is proposed to add the `CODE_OF_CONDUCT.md`.
# - ℹ️ If an issue is opened to suggest adding the `CODE_OF_CONDUCT.md`.

# ### 5. Issue Templates:
# - The repository must have the following issue templates:
#   - `bug_report.md`: Template for bug reports.
#   - `feature_request.md`: Template for feature requests.
# - ✅ The check will pass with a green check mark if both templates are present.
# - 🅿️ If a pull-request is proposed to add missing templates.
# - ℹ️ If an issue is opened to suggest adding missing templates.

# ### 6. PR Templates:
# - The repository must have a pull request (PR) template.
# - ✅ The check will pass with a green check mark if the PR template is present.
# - 🅿️ If a pull-request is proposed to add a PR template.
# - ℹ️ If an issue is opened to suggest adding a PR template.

# ### 7. Change Log:
# - The repository must contain a file named `CHANGELOG.md`.
# - ✅ The check will pass with a green check mark if this file is present.
# - 🅿️ If a pull-request is proposed to add the `CHANGELOG.md`.
# - ℹ️ If an issue is opened to suggest adding the `CHANGELOG.md`.

# ### 8. Additional Docs:
# - The README must contain a link to additional documentation, with a link label containing terms like "Docs", "Documentation", "Guide", "Tutorial", "Manual", "Instructions", "Handbook", "Reference", "User Guide", "Knowledge Base", or "Quick Start". Ex: "Unity-SPS Docs", "docs", or "Unity Documentation".
# - ✅ The check will pass with a green check mark if this link is present.
# - 🅿️ If a pull-request is proposed to add the link.
# - ℹ️ If an issue is opened to suggest adding the link.

# """

# # either write to file or print based on config
# if "output" in config:
#     with open(config["output"], "w") as file:
#         file.write(markdown_toc)
#         file.write(markdown_table)
#         file.write(markdown_report)
#         file.write(markdown_directions)
# else:
#     print("\n")
#     print(markdown_table)
