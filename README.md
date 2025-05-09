# SonarQube Cloud Project Creator

A utility script to automate the process of adding repositories from your DevOps Platform to a SonarQube Cloud organization.

## Features

- Lists available repositories that can be added to SonarQube Cloud Organization
- Allows adding specific repositories by filtering by label
- Supports automatic skipping of repositories already added to SonarQube Cloud
- Provides options for automated or interactive selection of repositories
- Can export repository information to a JSON file for reference
- Supports dry run mode to preview actions without making changes

## Prerequisites

- Python 3.6+
- SonarQube Cloud account with an organization
- Personal access token with sufficient permissions

## Installation

No special installation required beyond Python dependencies:

```bash
pip install requests
```

## Usage

Basic usage requires an organization key and token:

```bash

# Using environment variable for token
export SONAR_TOKEN=your-sonarqube-token
python sonarqube_project_creator.py --organization your-organization-key

# Explicitly providing token
python sonarqube_project_creator.py --organization your-organization-key --token your-sonarqube-token
```

### Command-line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--organization` | `-o` | **Required.** SonarQube Cloud organization key |
| `--token` | `-t` | SonarQube Cloud user token (if not provided, will look for SONAR_TOKEN env var or prompt) |
| `--all` | `-a` | Add all available repositories without prompting for selection |
| `--filter` | `-f` | Filter repositories by label (case-insensitive substring match) |
| `--repos` | | Specify one or more repository labels to add (exact match, case-sensitive) |
| `--output` | | Output file to save repository info (JSON format). If specified, only fetches repositories without provisioning |
| `--dry-run` | | Show what would be done without making actual changes |

### Common Workflows

1. **List all available repositories**:
   ```bash
   python sonarqube_project_creator.py --organization your-org --output repos.json --token your-sonarqube-token
   ```

2. **Add all repositories containing a specific term**:
   ```bash
   python sonarqube_project_creator.py --organization your-org --filter "api" --token your-sonarqube-token
   ```

3. **Add specific repositories by exact name**:
   ```bash
   python sonarqube_project_creator.py --organization your-org --repos "repo1" "repo2" "repo3" --token your-sonarqube-token
   ```

4. **Interactive selection with filtering**:
   ```bash
   python sonarqube_project_creator.py --organization your-org --token your-sonarqube-token
   ```

5. **Preview without making changes**:
   ```bash
   python sonarqube_project_creator.py --organization your-org --all --dry-run --token your-sonarqube-token
   ```

## Output File Format

When using the `--output` option, the script generates a JSON file with detailed information about repositories:

```json
{
  "repositories": [
    {
      "label": "example-repo",
      "installationKey": "org/example-repo|123456789",
      "slug": "org/example-repo",
      "private": false,
      "alreadyAdded": false,
      "linkedProjects": []
    },
    {
      "label": "another-repo",
      "installationKey": "org/another-repo|987654321",
      "slug": "org/another-repo",
      "private": true,
      "alreadyAdded": true,
      "linkedProjects": [
        {
          "key": "org-gh_another-repo",
          "name": "another-repo"
        }
      ]
    }
  ]
}
```

## Notes

- Repositories already added to SonarQube Cloud are automatically skipped during provisioning
- The script can handle a large number of repositories and provides clear output about what's being processed
- Use the `--output` option first to explore available repositories before applying filters
- The `--repos` parameter takes precedence over `--filter` and `--all` when specified
- The script will provide a list of the ProjectKey's for the projects created