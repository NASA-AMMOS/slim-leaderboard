
# SLIM Best Practices Repository Scan Report
| Owner | Repository | License | Readme | Contributing Guide | Code of Conduct | Issue Templates | PR Templates | Additional Documentation | Changelog | GitHub: Vulnerability Alerts | GitHub: Code Scanning Alerts | GitHub: Secret Scanning Alerts | Secrets Detection | Governance Model | Continuous Testing Plan |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nasa | fprime | 🟢 | 🟠 | 🟢 | 🟢 | 🟢 | 🔴 | 🟢 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 |


# Summary Statistics

| Metric | Value |
| ------ | ----- |
| Overall Best Practice Score (%) | 39.3 |
| License Score (%) | 100.0 |
| Contributing Guide Score (%) | 100.0 |
| Code of Conduct Score (%) | 100.0 |
| Issue Templates Score (%) | 100.0 |
| Additional Documentation Score (%) | 100.0 |
| Readme Score (%) | 50.0 |
| PR Templates Score (%) | 0.0 |
| Changelog Score (%) | 0.0 |
| GitHub: Vulnerability Alerts Score (%) | 0.0 |
| GitHub: Code Scanning Alerts Score (%) | 0.0 |
| GitHub: Secret Scanning Alerts Score (%) | 0.0 |
| Secrets Detection Score (%) | 0.0 |
| Governance Model Score (%) | 0.0 |
| Continuous Testing Plan Score (%) | 0.0 |
| Repositories evaluated (count) | 1 |
| Best practices checked (count) | 14 |
| PARTIAL (count) | 1 |
| YES (count) | 5 |
| NO (count) | 8 |


# Repository Check Explanation 

Each check against a repository will result in one of the following statuses:
- 🟢: The check passed, indicating that the repository meets the requirement.
- 🔴: The check failed, indicating that the repository does not meet the requirement.
- 🟠: The check passed conditionally, indicating that while the repository meets the requirement, improvements are needed.
- 🔵: Indicates there's an open issue ticket regarding the repository.
- 🟣: Indicates there's an open pull-request proposing a best practice.

## License
- The repository must contain a file named either `LICENSE` or `LICENSE.txt`.
- 🟢: The check will pass if either of these files is present.
- 🔴: The check will fail if neither file is present.
- 🟣: If a pull-request is proposed to add the `LICENSE` or `LICENSE.txt`.
- 🔵: If an issue is opened to suggest adding the `LICENSE` or `LICENSE.txt`.

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
- 🟢: If all these sections are present.
- 🟠: If the README file exists and has at least one section header but could use improvement in following best practices from SLIM.
- 🔴: If the README is missing or contains none of the required sections.
- 🟣: If a pull-request is proposed to add missing sections.
- 🔵: If an issue is opened to suggest adding missing sections.

## Contributing Guide:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/contributing-guide/

- The repository must contain a file named `CONTRIBUTING.md`.
- 🟢: The check will pass if this file is present.
- 🔴: The check will fail if this file is not present.
- 🟣: If a pull-request is proposed to add the `CONTRIBUTING.md`.
- 🔵: If an issue is opened to suggest adding the `CONTRIBUTING.md`.

## Code of Conduct:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/code-of-conduct/

- The repository must contain a file named `CODE_OF_CONDUCT.md`.
- 🟢: The check will pass if this file is present.
- 🔴: The check will fail if this file is not present.
- 🟣: If a pull-request is proposed to add the `CODE_OF_CONDUCT.md`.
- 🔵: If an issue is opened to suggest adding the `CODE_OF_CONDUCT.md`.

## Issue Templates:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/issue-templates/

- The repository must have the following issue templates: `bug_report.md` for bug reports and `feature_request.md` for feature requests.
- 🟢: The check will pass if both templates are present.
- 🔴: The check will fail if the templates are absent.
- 🟣: If a pull-request is proposed to add missing templates.
- 🔵: If an issue is opened to suggest adding missing templates.

## PR Templates:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/contributions/pull-requests/

- The repository must have a pull request (PR) template.
- 🟢: The check will pass if the PR template is present.
- 🔴: The check will fail if the PR template is absent.
- 🟣: If a pull-request is proposed to add a PR template.
- 🔵: If an issue is opened to suggest adding a PR template.

## Additional Documentation:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/documentation/documentation-hosts/trade-study-hostingdocs-user/

- The README must contain a link to additional documentation, with a link label containing terms like "Docs", "Documentation", "Guide", "Tutorial", "Manual", "Instructions", "Handbook", "Reference", "User Guide", "Knowledge Base", or "Quick Start".
- 🟢: The check will pass if this link is present.
- 🔴: The check will fail if no such link is present.
- 🟣: If a pull-request is proposed to add the link.
- 🔵: If an issue is opened to suggest adding the link.

## Change Log:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/documentation/change-log/

- The repository must contain a file named `CHANGELOG.md`.
- 🟢: The check will pass if this file is present.
- 🔴: The check will fail if this file is not present.
- 🟣: If a pull-request is proposed to add the `CHANGELOG.md`.
- 🔵: If an issue is opened to suggest adding the `CHANGELOG.md`.

## GitHub: Vulnerability Alerts:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/

- The repository must have GitHub Dependabot vulnerability alerts enabled.
- 🟢: The check will pass if this setting is enabled.
- 🔴: The check will fail if this setting is not enabled.

## GitHub: Code Scanning Alerts:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/

- The repository must have GitHub code scanning alerts enabled.
- 🟢: The check will pass if this setting is enabled.
- 🔴: The check will fail if this setting is not enabled.

## GitHub: Secrets Scanning Alerts:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/github-security/

- The repository must have GitHub secrets scanning alerts enabled.
- 🟢: The check will pass if this setting is enabled.
- 🔴: The check will fail if this setting is not enabled.


## Secrets Detection:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/security/secrets-detection/

- The repository must contain a file named `.secrets.baseline`, which represents the use of the detect-secrets tool.
- 🟢: The check will pass if this file is present.
- 🔴: The check will fail if no such file is present.
- 🟣: If a pull-request is proposed to add the file.
- 🔵: If an issue is opened to suggest adding the file.

## Governance Model:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/governance/governance-model/

- The repository must contain a file named `GOVERNANCE.md`.
- 🟢: The check will pass if this file is present.
- 🔴: The check will fail if no such file is present.
- 🟣: If a pull-request is proposed to add the file.
- 🔵: If an issue is opened to suggest adding the file.    

## Continuous Testing Plan:
View best practice guide: https://nasa-ammos.github.io/slim/docs/guides/software-lifecycle/continuous-testing/

- The repository must contain a file named `TESTING.md` that describes a continuous testing plan with required sections filled out.
- 🟢: The check will pass if this file is present and required sections such as "Static Code Analysis", "Unit Tests", "Security Tests", "Build Tests", "Acceptance Tests" exist.
- 🟠: If the TESTING.md file exists but is missing recommended sections
- 🔴: The check will fail if no such file is present.
- 🟣: If a pull-request is proposed to add the file.
- 🔵: If an issue is opened to suggest adding the file.  

