<!-- Header block for project -->
<hr>

<div align="center">

<h1 align="center">SLIM Best Practices Leaderboard</h1>

</div>

<pre align="center">Tool to generate a Markdown report of SLIM best practices compliance.</pre>

<!-- Header block for project -->

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md) [![SLIM](https://img.shields.io/badge/Best%20Practices%20from-SLIM-blue)](https://nasa-ammos.github.io/slim/)
<!-- ☝️ Add badges via: https://shields.io e.g. ![](https://img.shields.io/github/your_chosen_action/your_org/your_repo) ☝️ -->

This repository serves to create a leaderboard report (markdown table) that ranks and showcases how well a given set of GitHub repositories follow [SLIM best practices](https://nasa-ammos.github.io/slim/).

## Features

* Script to query a set of GitHub repositories and create a markdown table showcasing compliance to SLIM best practices, sorted by most to least compliant, printed to standard out and to an external file. 
* Best practices scanned for include:
  * Repository best practices (i.e. README, templates, licensing, etc.)
* Specification of repositories and API tokens via a config file - where repositories can be listed individually or automatically scanned from a parent organization.
* Works with GitHub.com or GitHub Enterprise repositories.
* API jittering to prevent too many fast requests to GitHub at once.
* Logging to share the status of repository compliance as the script runs.
  
## Contents

- [Features](#features)
- [Contents](#contents)
- [Quick Start](#quick-start)
  - [Setup Instructions](#setup-instructions)
  - [Run Instructions](#run-instructions)
- [Changelog](#changelog)
- [Frequently Asked Questions (FAQ)](#frequently-asked-questions-faq)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

## Quick Start

Use this quick start guide to generate a fresh leaderboard table. 

### Setup Instructions

You must have a configuration file to use this script. The purpose of the configuration file is:
- List the repositories to scan
- List the organizations to scan for repositories
- Point to the output file that will list the results
- Cite the GitHub personal access token used for authorization
  
This configuration file will be pointed to at runtime as an agrgument (see run instructions below). 

Below is a sample of a configuration file named `slim-config.json`:

```
{
    "gh_personal_access_token": "[INSERT_GITHUB_TOKEN_HERE]",
    "targets": [
        {
            "type": "organization",
            "name": "https://github.com/nasa-ammos"
        },
        {
            "type": "repository",
            "name": "https://github.com/nasa/FEI"
        },
        {
            "type": "repository",
            "name": "https://github.com/rzellem/EXOTIC"
        }
    ],
    "output": "slim-oss-leaderboard.md"
  }
  
```

### Run Instructions

Requirements: 
* Python 3
* `requests` module

Setup:
- Generate a GitHub personal access token and replace the string `TOKEN_GOES_HERE` with the value of your token. NOTE: make sure the "repo" group permission is enabled for your token within GitHub.com's personal access token setup.

To generate a fresh leaderboard markdown table (printed to `stdout`), run the following command:

```
python leaderboard.py [CONFIG_FILE]
```

Example:
```
python leaderboard.py slim-config.json
```

You'll see an output similar to the contents of the below sample:
| Project | Repository | [Issue Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/) | [PR Templates](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/change-request-templates/) | [Code of Conduct](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/) | [Contributing Guide](https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/) | LICENSE | [README](https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/) | [Change Log](https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/) | Link to Docs in README |
|---|---|---|---|---|---|---|---|---|---|
| [nasa-ammos](https://github.com/nasa-ammos) | [slim-starterkit](https://github.com/nasa-ammos/slim-starterkit) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [nasa-ammos](https://github.com/nasa-ammos) | [slim-starterkit-python](https://github.com/nasa-ammos/slim-starterkit-python) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [nasa-ammos](https://github.com/nasa-ammos) | [parent-ammos](https://github.com/nasa-ammos/parent-ammos) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| [nasa-ammos](https://github.com/nasa-ammos) | [slim](https://github.com/nasa-ammos/slim) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| [nasa-ammos](https://github.com/nasa-ammos) | [MMGIS](https://github.com/nasa-ammos/MMGIS) | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| 

How to interpret the leaderboard contents:
- A ✅ indicates successful compliance, where as a ❌ indicates not fully compliant
- Most checks verify whether files within your repository that should exist, do in fact exist. Some checks are more specialized, such as:
  - "README" - checks if your README conforms to the [SLIM standard README](https://nasa-ammos.github.io/slim/docs/guides/documentation/readme/)
  - "Dev/User Documentation" check for links to be present in your README that point to specific Dev or User docs - this is part of the SLIM standard README

## Changelog

See our root [CHANGELOG.md](CHANGELOG.md) for a history of our changes.

## Frequently Asked Questions (FAQ)

None. Please post a PR for this section to ask your question and the development team will add an answer.

## Contributing

Interested in contributing to our project? Please see our: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

See our: [LICENSE](LICENSE)

## Support

Key points of contact are: [@riverma](https://github.com/riverma)
