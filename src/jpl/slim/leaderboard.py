from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.tree import Tree
from tqdm import tqdm
from . import VERSION
import argparse
import json
import logging
import os, sys
import re
import requests
import textwrap
import traceback
import urllib.parse

logging.basicConfig(level=logging.INFO)
    
# Constants
STATUS_TO_EMOJI_MAPPING = {
    'YES': '🟢',
    'NO': '🔴',
    'PARTIAL': '🟠',
    'ISSUE': '🔵',
    'PR': '🟣'
}
STATUS_TO_COLOR_MAPPING = {
    'YES': 'green',
    'NO': 'red',
    'PARTIAL': 'yellow',
    'ISSUE': 'blue',
    'PR': 'blue'
}
STATUS_TO_SCORE_MAPPING = {
    'YES': 100,
    'NO': 0,
    'PARTIAL': 50,
    'ISSUE': 25,
    'PR': 25
}


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
        licenseMd: object(expression: "HEAD:LICENSE.md") {
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
        testing: object(expression: "HEAD:TESTING.md") {
          ... on Blob {
            text
          }
        }
        issues(first: 100, states: OPEN) {
          nodes {
            title
          }
        }
        pullRequests(first: 100, states: OPEN) {
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
            return 'YES'
        elif any(file_name in issue for issue in issues):
            return 'TICKET'
        elif any(file_name in pr['title'] or any(file_name in file for file in pr['files']) for pr in prs):
            return 'PR'
        else:
            return 'NO'

    if response.status_code == 200:
        result = response.json()

        if not result.get('errors'):  # Process as long as results are clean
            issues = [
                issue['title']
                for issue in result.get('data', {}).get('repository', {}).get('issues', {}).get('nodes', [])
                if issue and 'title' in issue  # Ensure 'issue' is a dictionary and has the key 'title'
            ]
            pull_requests = [{
                'title': pr['title'],
                'files': [file['path'] for file in pr.get('files', {}).get('nodes', [])] if pr.get('files') else []
            } for pr in result['data']['repository']['pullRequests']['nodes']]

            # README in-depth checks
            readme_text = result['data']['repository']['readme']['text'] if result['data']['repository']['readme'] else ""
            readme_required_sections = ["Features", "Contents", "Quick Start", "Changelog", "Frequently Asked Questions (FAQ)", "Contributing", "License", "Support"]
            readme_sections = re.findall(r'^#+\s*(.*)$', readme_text, re.MULTILINE)
            if all(section in readme_sections for section in readme_required_sections):
                readme_check = 'YES'
            elif len(readme_sections) > 0:
                readme_check = 'PARTIAL'
            else:
                readme_check = generate_check_mark('README.md', None, issues, pull_requests)
            docs_link_check = 'YES' if re.search(r'\b(?:Docs|Documentation|Guide|Tutorial|Manual|Instructions|Handbook|Reference|User Guide|Knowledge Base|Quick Start)\b(?:\s*\[\s*.*?\s*\]\s*\(\s*[^)]*\s*\))?', readme_text, re.IGNORECASE) else 'NO'

            # TESTING.md in-depth checks
            testing_text = result['data']['repository']['testing']['text'] if result['data']['repository']['testing'] else ""
            testing_required_sections = ["Static Code Analysis", "Unit Tests", "Security Tests", "Build Tests", "Acceptance Tests"]
            testing_sections = re.findall(r'^#+\s*(.*)$', testing_text, re.MULTILINE)
            if all(section in testing_sections for section in testing_required_sections):
                testing_check = 'YES'
            elif len(testing_text) > 0:
                testing_check = 'PARTIAL'
            else:
                testing_check = generate_check_mark('TESTING.md', None, issues, pull_requests)

            checks = {
                'owner': owner,
                'repo': repo_name,
                'readme': readme_check,
                'license': generate_check_mark('LICENSE', result['data']['repository']['license'] or result['data']['repository']['licenseTxt'] or result['data']['repository']['licenseMd'], issues, pull_requests),
                'contributing': generate_check_mark('CONTRIBUTING.md', result['data']['repository']['contributing'], issues, pull_requests),
                'code_of_conduct': generate_check_mark('CODE_OF_CONDUCT.md', result['data']['repository']['code_of_conduct'], issues, pull_requests),
                'issue_templates': generate_check_mark('.github/ISSUE_TEMPLATE', result['data']['repository']['issue_templates'], issues, pull_requests),
                'pull_request_template': generate_check_mark('PULL_REQUEST_TEMPLATE.md', result['data']['repository']['pull_request_template'], issues, pull_requests),
                'changelog': generate_check_mark('CHANGELOG.md', result['data']['repository']['changelog'], issues, pull_requests),
                'docs_link_check': docs_link_check,
                'secrets_baseline': generate_check_mark('.secrets.baseline', result['data']['repository']['secrets_baseline'], issues, pull_requests),
                'governance': generate_check_mark('GOVERNANCE.md', result['data']['repository']['governance'], issues, pull_requests),
                'testing': testing_check
            }
            return checks
        else:
            logging.warning(f"Invalid or malformed response to checks for {owner}/{repo_name} at {api_url}: {response.status_code} - {response.text}")
            return None
    else:
        logging.error(f"Failed to check file existence for {owner}/{repo_name} at {api_url}: {response.status_code} - {response.text}")
        return None


def process_repository(repo_full_name, headers):
    try:
        owner, repo_name = repo_full_name.split('/')[-2:]
        hostname = urllib.parse.urlparse(repo_full_name).hostname
        graphql_api_url = "https://api.github.com/graphql" if hostname == "github.com" else f"https://{hostname}/api/graphql"
        rest_api_url = f"https://api.github.com/repos/{owner}/{repo_name}" if hostname == "github.com" else f"https://{hostname}/api/v3/repos/{owner}/{repo_name}"

        checks = check_files_existence(owner, repo_name, graphql_api_url, headers)
        status_codes = fetch_status_codes(rest_api_url,
            ["/vulnerability-alerts",
             "/code-scanning/alerts",
             "/secret-scanning/alerts"],
             headers
        )

        status_checks = {}
        status_checks['/vulnerability-alerts'] = 'YES' if status_codes['/vulnerability-alerts'] == 204 else 'NO'
        status_checks['/code-scanning/alerts'] = 'YES' if status_codes['/code-scanning/alerts'] == 200 else 'NO'
        status_checks['/secret-scanning/alerts'] = 'YES' if status_codes['/secret-scanning/alerts'] == 200 else 'NO'
        
        # Safely merge checks
        if checks and status_checks:
            result = checks | status_checks
        else:
            result = None

        return result

    except Exception as e:
        logging.error(f"Error processing repository {repo_full_name}: {e}")
        traceback.print_exc()
        return {'repo_full_name': repo_full_name}


def calculate_column_statistics(rows, headers):
    """Calculate average scores for each column."""
    column_scores = {}
    column_counts = {}
    
    for _, label in headers:
        if label not in ['Owner', 'Repository']:  # Skip non-score columns
            column_scores[label] = 0
            column_counts[label] = 0
    
    for row in rows:
        for key, label in headers:
            if key not in ['owner', 'repo']:  # Skip owner and repo columns
                if row[key] in STATUS_TO_SCORE_MAPPING:
                    column_scores[label] += STATUS_TO_SCORE_MAPPING[row[key]]
                    column_counts[label] += 1
    
    # Calculate averages
    column_averages = {}
    for label in column_scores:
        if column_counts[label] > 0:
            column_averages[label] = round(column_scores[label] / column_counts[label], 2)
        else:
            column_averages[label] = 0
            
    # Sort by average score
    sorted_averages = dict(sorted(column_averages.items(), key=lambda x: x[1], reverse=True))
    return sorted_averages


def main():
    """Main entrypoint."""
    # load configuration from external JSON file
    # accept configuration file path from command-line argument
    parser = argparse.ArgumentParser(description="SLIM Best Practices Leaderboard Script")
    parser.add_argument("config_path", help="Path to the JSON configuration file")
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--output_format', choices=['TREE', 'TABLE', 'MARKDOWN', 'PLAIN'], default='TREE', type=str, help='Output formatting')
    parser.add_argument('--unsorted', action='store_true', default=False, help='Do not sort results')
    parser.add_argument('--verbose', action='store_true', default=False, help='Output verbose information, inluding statistics and explanations')
    parser.add_argument('--emoji', action='store_true', default=False, help='Use pretty emojis for status instead of text')
    args = parser.parse_args()

    # load configuration from provided file path
    with open(args.config_path, "r") as file:
        config = json.load(file)

    # Get the GitHub authentication token from the environment variable
    auth_token = os.getenv("GITHUB_TOKEN")

    if not auth_token:
        sys.stderr.write("Error: GITHUB_TOKEN environment variable is empty. Please provide a valid GitHub Personal Access Token.\n")
        sys.exit(1)

    headers = {"Authorization": f"token {auth_token}"}
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
                        if (repo['archived'] or repo['disabled']):  # ignore archived and disabled repositories
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

    rows = []

    for repo in tqdm(repos_list, desc="Scanning Repositories", unit="repo"):
        processed_repo = process_repository(repo, headers)
        if processed_repo:
            rows.append(processed_repo)

    # Optionally sort rows by highest passing score to lowest
    if not args.unsorted:
        def count_pass_values(row):
            """Count the number of 'YES' values in the dictionary."""
            return sum(1 for key in row if row[key] == 'YES')
        rows = sorted(rows, key=count_pass_values, reverse=True)

    # Calculate stats
    status_counts = Counter()
    for row in rows:
        status_counts.update(row.values())  # Update the counter based on values in each row

    console = Console()

    def style_status_for_terminal(status, emoji=False):
        styled_status = ''
        if emoji:
            icon = STATUS_TO_EMOJI_MAPPING.get(status, status)  # Default to text if emoji mapping not found
            styled_status = icon
        else:
            color = STATUS_TO_COLOR_MAPPING.get(status, 'black')  # Default to black if emoji mapping not found
            styled_status = f"[{color}]{status}[/{color}]"
        
        return styled_status

    def style_status_for_markdown(status, emoji=False):
        styled_status = ''
        if emoji:
            icon = STATUS_TO_EMOJI_MAPPING.get(status, status)  # Default to text if emoji mapping not found
            styled_status = icon
        else:
            styled_status = status  # Markdown doesn't support colored text, so just use no styling
        
        return styled_status

    # Define the headers and corresponding labels
    headers = [
        ("owner", "Owner"),
        ("repo", "Repository"),
        ("license", "License"),
        ("readme", "Readme"),
        ("contributing", "Contributing Guide"),
        ("code_of_conduct", "Code of Conduct"),
        ("issue_templates", "Issue Templates"),
        ("pull_request_template", "PR Templates"),
        ("docs_link_check", "Additional Documentation"),
        ("changelog", "Changelog"),
        ("/vulnerability-alerts", "GitHub: Vulnerability Alerts"),
        ("/code-scanning/alerts", "GitHub: Code Scanning Alerts"),
        ("/secret-scanning/alerts", "GitHub: Secret Scanning Alerts"),
        ("secrets_baseline", "Secrets Detection"),
        ("governance", "Governance Model"),
        ("testing", "Continuous Testing Plan")
    ]

    if args.output_format == 'TREE':
        tree = Tree("SLIM Best Practices Repository Scan Report")
        for row in rows:
            if 'owner' in row and 'repo' in row:
                repo_branch = tree.add(f"[bold magenta]{row['owner']}/{row['repo']}[/bold magenta]")
                for key, label in headers:
                    if key not in ['owner', 'repo']:  # ignore owner and repo for the tree list since we printed it above already
                        repo_branch.add(f"[{style_status_for_terminal(row[key], args.emoji)}] {label}") 
        console.print(tree)

    elif args.output_format == 'PLAIN':
        console.print("SLIM Best Practices Repository Scan Report", style="bold")
        for row in rows:
            console.print(f"[bold magenta]{row['owner']}/{row['repo']}[/bold magenta]")
            for key, label in headers:
                if key not in ['owner', 'repo']:  # ignore owner and repo for the tree list since we printed it above already
                    console.print(f"- [{style_status_for_terminal(row[key], args.emoji)}] {label}") 

    elif args.output_format == 'TABLE':
        table = Table(title="SLIM Best Practices Repository Scan Report", show_header=True, header_style="bold magenta", show_lines=True)
        for _, label in headers:
            table.add_column(label)
        for row in rows:
            table.add_row(*[style_status_for_terminal(row[key], args.emoji) for key, _ in headers])
        console.print(table)

    elif args.output_format == 'MARKDOWN':
        # Create the header row
        header_row = '| ' + ' | '.join([label for _, label in headers]) + ' |'
        # Create the separator row
        separator_row = '| ' + ' | '.join(['---'] * len(headers)) + ' |'
        # Create all data rows
        data_rows = [
            '| ' + ' | '.join([style_status_for_markdown(row[key], args.emoji) for key, _ in headers]) + ' |'
            for row in rows
        ]
        markdown_table = '\n'.join([header_row, separator_row] + data_rows)
        print()
        print("# SLIM Best Practices Repository Scan Report")
        print(markdown_table)  # Or use Markdown rendering if required

    else:
        logging.error(f"Invalid --output_format specified: {args.output_format}.")

    if args.verbose:
        # Summary statistics
        print()

        # calculate counts for repositories and standards
        repos_count = len(rows)
        standards_count = len(headers) - 2 # ignore column 1 and 2 which are irrelevant

        column_averages = calculate_column_statistics(rows, headers)

        # build list of all numeric scores, used for overall average
        all_scores = list(column_averages.values())
        overall_average = sum(all_scores) / len(all_scores) if all_scores else 0

        # create a list of final rows in the desired order:
        # 1) overall best practice score
        # 2) each best practice's score
        # 3) repositories evaluated (count)
        # 4) best practices checked (count)
        # 5) all status counts
        summary_rows = []

        # add overall best practice score
        summary_rows.append(("Overall Best Practice Score (%)", f"{overall_average:.1f}"))

        # add best practice scores (top of the table)
        for category, score in column_averages.items():
            summary_rows.append((f"{category} Score (%)", f"{score:.1f}"))

        # add repository/standards counts
        summary_rows.append(("Repositories evaluated (count)", str(repos_count)))
        summary_rows.append(("Best practices checked (count)", str(standards_count)))

        # add status counts (bottom of the table)
        for status, count in status_counts.items():
            if status in ['YES', 'NO', 'PARTIAL', 'PR', 'ISSUE']:
                summary_rows.append((f"{status} (count)", str(count)))

        if args.output_format == "MARKDOWN":
            # build one Markdown table for everything
            markdown_table = textwrap.dedent("""
            # Summary Statistics

            | Metric | Value |
            | ------ | ----- |
            """)
            
            # add all rows in order
            for metric, value in summary_rows:
                markdown_table += f"| {metric} | {value} |\n"

            console.print(markdown_table)

        elif args.output_format == "PLAIN":
            # print single "table" for summary stats in plain text
            console.print("[b]Summary Statistics[/b]")
            console.print("Metric | Value")
            console.print("------ | -----")

            # add all rows in order
            for metric, value in summary_rows:
                console.print(f"{metric} | {value}")

        else:
            # create a single Rich table for everything
            summary_table = Table(title="Summary Statistics", show_header=True, header_style="bold")
            summary_table.add_column("Metric", style="dim", width=35)
            summary_table.add_column("Value", justify="right")

            # add all rows in order
            for metric, value in summary_rows:
                summary_table.add_row(metric, value)

            console.print(summary_table)

        # Explanations
        markdown_explanations = textwrap.dedent(f"""
        # Repository Check Explanation 

        Each check against a repository will result in one of the following statuses:
        - {style_status_for_markdown('YES', args.emoji)}: The check passed, indicating that the repository meets the requirement.
        - {style_status_for_markdown('NO', args.emoji)}: The check failed, indicating that the repository does not meet the requirement.
        - {style_status_for_markdown('PARTIAL', args.emoji)}: The check passed conditionally, indicating that while the repository meets the requirement, improvements are needed.
        - {style_status_for_markdown('ISSUE', args.emoji)}: Indicates there's an open issue ticket regarding the repository.
        - {style_status_for_markdown('PR', args.emoji)}: Indicates there's an open pull-request proposing a best practice.

        ## License
        - The repository must contain a file named either `LICENSE` or `LICENSE.txt`.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if either of these files is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if neither file is present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the `LICENSE` or `LICENSE.txt`.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the `LICENSE` or `LICENSE.txt`.

        ## README
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/

        - The README must contain sections with the following titles: 
            - "Features"
            - "Contents"
            - "Quick Start"
            - "Changelog"
            - "Frequently Asked Questions (FAQ)"
            - "Contributing"
            - "License"
            - "Support"
        - {style_status_for_markdown('YES', args.emoji)}: If all these sections are present.
        - {style_status_for_markdown('PARTIAL', args.emoji)}: If the README file exists and has at least one section header but could use improvement in following best practices from SLIM.
        - {style_status_for_markdown('NO', args.emoji)}: If the README is missing or contains none of the required sections.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add missing sections.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding missing sections.

        ## Contributing Guide:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/

        - The repository must contain a file named `CONTRIBUTING.md`.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this file is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if this file is not present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the `CONTRIBUTING.md`.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the `CONTRIBUTING.md`.

        ## Code of Conduct:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/

        - The repository must contain a file named `CODE_OF_CONDUCT.md`.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this file is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if this file is not present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the `CODE_OF_CONDUCT.md`.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the `CODE_OF_CONDUCT.md`.

        ## Issue Templates:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/

        - The repository must have the following issue templates: `bug_report.md` for bug reports and `feature_request.md` for feature requests.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if both templates are present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if the templates are absent.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add missing templates.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding missing templates.

        ## PR Templates:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/pull-requests/

        - The repository must have a pull request (PR) template.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if the PR template is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if the PR template is absent.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add a PR template.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding a PR template.

        ## Additional Documentation:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/documentation/documentation-hosts/trade-study-hostingdocs-user/

        - The README must contain a link to additional documentation, with a link label containing terms like "Docs", "Documentation", "Guide", "Tutorial", "Manual", "Instructions", "Handbook", "Reference", "User Guide", "Knowledge Base", or "Quick Start".
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this link is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if no such link is present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the link.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the link.
        
        ## Change Log:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/

        - The repository must contain a file named `CHANGELOG.md`.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this file is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if this file is not present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the `CHANGELOG.md`.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the `CHANGELOG.md`.

        ## GitHub: Vulnerability Alerts:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/

        - The repository must have GitHub Dependabot vulnerability alerts enabled.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this setting is enabled.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if this setting is not enabled.

        ## GitHub: Code Scanning Alerts:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/

        - The repository must have GitHub code scanning alerts enabled.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this setting is enabled.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if this setting is not enabled.

        ## GitHub: Secrets Scanning Alerts:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/

        - The repository must have GitHub secrets scanning alerts enabled.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this setting is enabled.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if this setting is not enabled.


        ## Secrets Detection:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/secrets-detection/

        - The repository must contain a file named `.secrets.baseline`, which represents the use of the detect-secrets tool.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this file is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if no such file is present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the file.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the file.

        ## Governance Model:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/governance-model/

        - The repository must contain a file named `GOVERNANCE.md`.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this file is present.
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if no such file is present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the file.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the file.    

        ## Continuous Testing Plan:
        View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/continuous-testing/

        - The repository must contain a file named `TESTING.md` that describes a continuous testing plan with required sections filled out.
        - {style_status_for_markdown('YES', args.emoji)}: The check will pass if this file is present and required sections such as "Static Code Analysis", "Unit Tests", "Security Tests", "Build Tests", "Acceptance Tests" exist.
        - {style_status_for_markdown('PARTIAL', args.emoji)}: If the TESTING.md file exists but is missing recommended sections
        - {style_status_for_markdown('NO', args.emoji)}: The check will fail if no such file is present.
        - {style_status_for_markdown('PR', args.emoji)}: If a pull-request is proposed to add the file.
        - {style_status_for_markdown('ISSUE', args.emoji)}: If an issue is opened to suggest adding the file.  
        """)

        if args.output_format == "MARKDOWN":  # If markdown styling specified, will just print pure Markdown text not rendered
            print(markdown_explanations)
        else:
            console.print(Markdown(markdown_explanations))  


if __name__ == '__main__':
    main()
