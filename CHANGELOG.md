# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added `--repositories` command-line argument to allow direct specification of repositories without requiring a configuration file for quick checks
- Made configuration file optional when using the `--repositories` argument

### Fixed

- Fixed LibreSSL compatibility warning by pinning urllib3 to v1.x

## [1.1.0] - 2024-01-28

### Added

- Requests-caching for faster retrieval / generation of reports
- Checking for open pull requests and issue tickets relating to best practice proposal as well as existing checks for best practice infusion in repos
- Summarization reports for checks

### Changed

- Markdown reports are more usable and have explanation for checks

## [1.0.0] - 2023-10-11

### Added

- Initial commit of report generation tool
