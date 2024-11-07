<!-- Header block for project -->
<hr>

<div align="center">

<h1 align="center">SLIM Best Practices Leaderboard</h1>

</div>

<pre align="center">Tool to generate a scan report of SLIM best practices compliance.</pre>

<!-- Header block for project -->

[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](code_of_conduct.md) [![SLIM](https://img.shields.io/badge/Best%20Practices%20from-SLIM-blue)](https://nasa-ammos.github.io/slim/)
<!-- ☝️ Add badges via: https://shields.io e.g. ![](https://img.shields.io/github/your_chosen_action/your_org/your_repo) ☝️ -->

This repository serves to create a leaderboard report that ranks and showcases how well a given set of GitHub repositories follow [SLIM best practices](https://nasa-ammos.github.io/slim/).

## Features

* Script to query a set of GitHub repositories and create a report showcasing compliance to SLIM best practices, sorted by most to least compliant, printed to standard out. 
* Best practices scanned for include all checklist items specified in the [SLIM Getting Started Checklist](https://nasa-ammos.github.io/slim/docs/guides/checklist#checklist)
* Specification of repositories via a config file - where repositories can be listed individually or automatically scanned from a parent organization.
* Works with GitHub.com or GitHub Enterprise repositories.
* GraphQL and parallelized queries to GitHub for optimization
* Logging to share the status of repository compliance as the script runs.
* Output format modes including: tree, table, and markdown
* Verbose mode for additional statistical details and explanations
  
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

Use this quick start guide to generate a fresh leaderboard report. 


### Setup Instructions

This script requires a configuration file to operate. This file specifies the repositories and organizations to scan.

Below is an example of a configuration file named `slim-config.json`:

```json
{
  "targets": [
      {
        "type": "repository",
        "name": "https://github.com/nasa-ammos/slim"
      }
  ]
}
```

Additional examples can be found in the `examples/` sub-folder within [the source repository](https://github.com/NASA-AMMOS/slim-leaderboard).


### Run Instructions

**Requirements:**

This software requires [Python 3.7 or later](https://www.python.org/). Usually, you'll want to create a virtual environment in order to isolate the dependencies of SLIM Leaderboard from other Python-using applications. Install SLIM Leaderboard into that environment using `pip`:

    pip install slim-leaderboard

This installs the latest SLIM Leaderboard and its dependencies from the [Python Package Index](https://pypi.org/). The new console script `slim-leaderboard` is now ready for use. Confirm by running either:

    slim-leaderboard --version
    slim-leaderboard --help

To upgrade:

    pip install --upgrade slim-leaderboard

Or select a specific version, such as `X.Y.Z`:

    pip install slim-leaderboard==X.Y.Z

You'll also need a GitHub personal access token (classic). Ensure that all permissions under the "repo" group are enabled for this token, including `security_events`. Set the environment variable `GITHUB_TOKEN` with your token.

**Execution:**

**👉 Note:** the below example outputs will change as the tool evolves and adds more checks. This is for demonstration purposes only.

To generate a fresh leaderboard report, use the following command format:

    slim-leaderboard --output_format FORMAT --unsorted --verbose --emoji CONFIG_FILE

The arguments above are as follows:

- `CONFIG_FILE`: Path to the JSON configuration file.
- (Optional) `--output_format FORMAT`: Replace `FORMAT` with `TREE`, `TABLE`, `MARKDOWN`, or `PLAIN`. Default is `TREE`.
- (Optional) `--unsorted`: If included, the results will not be sorted.
- (Optional) `--verbose`: If included, outputs verbose information, including detailed statistics and explanations for each check performed.
- (Optional) `--emoji`: If included, outputs emojis for statuses rathe than pure text (e.g. ✅ ❌ ⚠️ etc.)

**Examples:**

Generate a report using default settings:

    slim-leaderboard slim-config.json

![tree](https://github.com/user-attachments/assets/f9ff8de4-2c8f-48dd-9475-ea04a3ba49f0)

Generate a report in table format:

    slim-leaderboard --output_format TABLE slim-config.json

![table](https://github.com/user-attachments/assets/84d99076-89e4-48c1-84bc-4cfc245f173b)

Verbose output in tree format:

    slim-leaderboard --output_format TREE --verbose slim-config.json

![tree-verbose](https://github.com/user-attachments/assets/854aacf4-ce52-4819-a5f5-05a8f8684376)


Markdown format without sorting and with emojis:

    slim-leaderboard --output_format MARKDOWN --unsorted --emoji slim-config.json 


```
Scanning Repositories: 100%|█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 2/2 [00:02<00:00,  1.15s/repo]

# SLIM Best Practices Repository Scan Report
| Owner | Repository | License | Readme | Contributing Guide | Code of Conduct | Issue Templates | PR Templates | Changelog | Additional Documentation | Secrets Detection | Governance Model | GitHub: Vulnerability Alerts | GitHub: Code Scanning Alerts | GitHub: Secret Scanning Alerts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nasa-ammos | slim | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| NASA-AMMOS | slim-starterkit-python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
```

## Changelog

See our root [CHANGELOG.md](CHANGELOG.md) for a history of our changes.


## Frequently Asked Questions (FAQ)

None. Please post a PR for this section to ask your question and the development team will add an answer.


## Contributing

Interested in contributing to our project? Please see our: [CONTRIBUTING.md](CONTRIBUTING.md)


### Local Development

For local development of SLIM Leaderboard, clone the GitHub repository, create a virtual environment, and then install the package in editable mode into it. For example:
```sh
$ git clone --quiet https://github.com/NASA-AMMOS/slim-leaderboard.git
$ cd slim-leaderboard
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install --editable .
```

The `slim-leaderboard` console-script is now ready in editable mode; changes you make to the source files under `src` are immediately reflected when run.


## License

See our: [LICENSE](LICENSE)


## Support

Key points of contact are: [@riverma](https://github.com/riverma)


