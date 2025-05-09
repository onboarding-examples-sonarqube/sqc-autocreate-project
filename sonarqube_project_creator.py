#!/usr/bin/env python3
"""
Script to automate adding GitHub repositories to a SonarQube Cloud organization.

This script:
1. Gets the list of available repositories for a SonarCloud organization
2. Extracts installation keys for each repository
3. Provisions selected repositories to the SonarCloud organization
"""

import requests
import argparse
import json
import sys
from typing import List, Dict, Any, Optional
import os
from getpass import getpass


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Add GitHub repositories to a SonarQube Cloud organization."
    )
    parser.add_argument(
        "--organization", "-o", 
        required=True,
        help="SonarQube Cloud organization key"
    )
    parser.add_argument(
        "--token", "-t",
        help="SonarQube Cloud user token (if not provided, will prompt or use SONAR_TOKEN env var)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Add all available repositories (otherwise will prompt for selection)"
    )
    parser.add_argument(
        "--filter", "-f",
        help="Filter repositories by label (case-insensitive substring match)"
    )
    parser.add_argument(
        "--output", 
        help="Output file to save repository info (JSON format). If specified, only fetches repositories without provisioning."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making actual changes"
    )
    parser.add_argument(
        "--repos",
        nargs="+",
        help="Specify one or more repository labels to add (exact match, case-sensitive)"
    )
    return parser.parse_args()


def get_sonar_token(args) -> str:
    """Get SonarQube token from args, environment or prompt."""
    if args.token:
        return args.token
    
    token = os.environ.get("SONAR_TOKEN")
    if token:
        return token
    
    return getpass("Enter your SonarQube token: ")


def list_available_repositories(organization: str, token: str) -> List[Dict[str, Any]]:
    """
    Get list of available repositories that can be added to SonarCloud organization.
    
    Args:
        organization: SonarQube Cloud organization key
        token: SonarQube token
        
    Returns:
        List of repositories with their details
    """
    url = "https://sonarcloud.io/api/alm_integration/list_repositories"
    params = {"organization": organization}
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        return response.json().get("repositories", [])
    except requests.RequestException as e:
        print(f"Error fetching repositories: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)


def filter_unlinked_repositories(repositories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter repositories to include only those not yet added to SonarQube Cloud.
    
    Args:
        repositories: List of repositories
        
    Returns:
        List of repositories that haven't been added to SonarQube Cloud
    """
    unlinked_repos = []
    linked_repos = []
    
    for repo in repositories:
        if not repo.get("linkedProjects"):
            unlinked_repos.append(repo)
        else:
            linked_repos.append(repo)
    
    if linked_repos:
        print(f"\nSkipping {len(linked_repos)} repositories already added to SonarQube Cloud:")
        for repo in linked_repos:
            project_names = [p.get("name") for p in repo.get("linkedProjects", [])]
            print(f"- {repo.get('label')} (linked to: {', '.join(project_names)})")
    
    return unlinked_repos


def provision_projects(organization: str, token: str, installation_keys: List[str]) -> Dict[str, Any]:
    """
    Provision projects to SonarCloud organization.
    
    Args:
        organization: SonarQube Cloud organization key
        token: SonarQube token
        installation_keys: List of installation keys to provision
        
    Returns:
        API response data
    """
    url = "https://sonarcloud.io/api/alm_integration/provision_projects"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        # Join installation keys as a comma-separated string
        comma_separated_keys = ",".join(installation_keys)
        
        # Build the data payload with comma-separated installation keys
        data = {
            "organization": organization,
            "installationKeys": comma_separated_keys
        }
        
        # Use the requests library with proper encoding
        response = requests.post(
            url,
            data=data,
            headers=headers
        )
        
        response.raise_for_status()
        
        return response.json()
    except requests.RequestException as e:
        print(f"Error provisioning projects: {e}")
        if hasattr(e, "response") and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)


def select_repositories(repositories: List[Dict[str, Any]], filter_text: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Allow user to select repositories from list.
    
    Args:
        repositories: List of repositories
        filter_text: Optional text to filter repositories
        
    Returns:
        List of selected repositories
    """
    if filter_text:
        filtered_repos = [
            repo for repo in repositories 
            if filter_text.lower() in repo.get("label", "").lower()
        ]
    else:
        filtered_repos = repositories
    
    if not filtered_repos:
        print("No repositories match the filter criteria.")
        return []
    
    print("\nAvailable repositories:")
    for i, repo in enumerate(filtered_repos, 1):
        print(f"{i}. {repo.get('label')} ({repo.get('slug')})")
    
    selection = input("\nEnter numbers of repositories to add (comma-separated) or 'all': ")
    
    if selection.lower() == "all":
        return filtered_repos
    
    try:
        indices = [int(idx.strip()) - 1 for idx in selection.split(",")]
        return [filtered_repos[idx] for idx in indices if 0 <= idx < len(filtered_repos)]
    except (ValueError, IndexError):
        print("Invalid selection. Please provide valid numbers.")
        return select_repositories(repositories, filter_text)


def save_repository_info(repositories: List[Dict[str, Any]], filename: str):
    """Save repository information to a file."""
    data = {
        "repositories": [{
            "label": repo.get("label"),
            "installationKey": repo.get("installationKey"),
            "slug": repo.get("slug"),
            "private": repo.get("private", False),
            "alreadyAdded": bool(repo.get("linkedProjects")),
            "linkedProjects": repo.get("linkedProjects", [])
        } for repo in repositories]
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Repository information saved to {filename}")


def save_installation_keys(repositories: List[Dict[str, Any]], filename: str):
    """Save installation keys to a file."""
    data = {
        "installationKeys": [repo.get("installationKey") for repo in repositories],
        "repositories": [{
            "name": repo.get("name"),
            "slug": repo.get("slug"),
            "installationKey": repo.get("installationKey")
        } for repo in repositories]
    }
    
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"Installation keys saved to {filename}")


def main():
    """Main function to run the script."""
    args = parse_arguments()
    organization = args.organization
    token = get_sonar_token(args)
    
    print(f"Fetching available repositories for organization '{organization}'...")
    repositories = list_available_repositories(organization, token)
    
    if not repositories:
        print("No repositories found that can be added.")
        sys.exit(0)
    
    print(f"Found {len(repositories)} repositories.")
    
    # If output file is specified, save all repositories to file and exit
    # This should happen before filtering so users can first see all available repositories
    if args.output:
        save_repository_info(repositories, args.output)
        print(f"Repository information for all {len(repositories)} repositories saved to {args.output}.")
        print("Use this file to identify labels for filtering in subsequent runs.")
        print("Exiting without provisioning projects.")
        sys.exit(0)
    
    # Filter out repositories that have already been added to SonarQube Cloud
    repositories = filter_unlinked_repositories(repositories)
    
    if not repositories:
        print("No repositories available to add (all are already linked to SonarQube Cloud).")
        sys.exit(0)
    
    print(f"Found {len(repositories)} repositories that can be added to SonarQube Cloud.")
    
    # Handle repository selection based on arguments
    if args.repos:
        # If specific repos are specified, select them by exact label match
        repo_labels = args.repos
        filtered_repos = []
        
        # Debug output to verify label matching
        print(f"Looking for repositories with labels: {', '.join(repo_labels)}")
        
        # Create a case-insensitive matching for better user experience
        for repo in repositories:
            repo_label = repo.get("label", "")
            # Check if the repo label is in the requested labels (case insensitive)
            if any(label.lower() == repo_label.lower() for label in repo_labels):
                filtered_repos.append(repo)
        
        if not filtered_repos:
            print("None of the specified repositories were found or are available to add.")
            sys.exit(0)
        
        # Report if some repos weren't found
        found_labels = [repo.get("label") for repo in filtered_repos]
        print(f"Found repositories: {', '.join(found_labels)}")
        
        not_found = []
        for label in repo_labels:
            if not any(label.lower() == found.lower() for found in found_labels):
                not_found.append(label)
        
        if not_found:
            print("\nWarning: The following repositories were not found or are already linked:")
            for label in not_found:
                print(f"- {label}")
        
        print(f"\nSelected {len(filtered_repos)} repositories:")
        for repo in filtered_repos:
            print(f"- {repo.get('label')} ({repo.get('slug')})")
        
        selected_repos = filtered_repos
    elif args.filter:
        # If filter is specified, automatically select all matching repositories without prompting
        filtered_repos = [
            repo for repo in repositories 
            if args.filter.lower() in repo.get("label", "").lower()
        ]
        if not filtered_repos:
            print(f"No available repositories match the filter criteria '{args.filter}'.")
            sys.exit(0)
        
        print(f"\nAutomatically selected {len(filtered_repos)} repositories matching filter '{args.filter}':")
        for repo in filtered_repos:
            print(f"- {repo.get('label')} ({repo.get('slug')})")
        
        selected_repos = filtered_repos
    elif args.all:
        # Select all repositories if --all is specified
        selected_repos = repositories
        print(f"Selected all {len(selected_repos)} repositories.")
    else:
        # Otherwise use interactive selection
        selected_repos = select_repositories(repositories, None)
    
    if not selected_repos:
        print("No repositories selected. Exiting.")
        sys.exit(0)
    
    # Extract installation keys
    installation_keys = [repo.get("installationKey") for repo in selected_repos]
    
    # Confirm with user
    repo_labels = [repo.get("label") for repo in selected_repos]
    print(f"\nAbout to add {len(selected_repos)} repositories to SonarQube Cloud:")
    for label in repo_labels:
        print(f"- {label}")
    
    confirmation = input("\nContinue? (y/N): ")
    if confirmation.lower() != "y":
        print("Operation cancelled.")
        sys.exit(0)
    
    print("\nProvisioning projects in SonarQube Cloud...")
    
    # Handle dry run mode
    if args.dry_run:
        print("DRY RUN MODE: Would provision the following projects:")
        for label in repo_labels:
            print(f"- {label}")
        print("No changes were made to SonarQube Cloud.")
        sys.exit(0)
    
    result = provision_projects(organization, token, installation_keys)
    
    print("\nProject provisioning completed!")
    print(f"Projects added: {len(result.get('projects', []))}")
    
    for project in result.get('projects', []):
        # Just use the project key from the response
        project_key = project.get('projectKey')
        print(f"- Project Key: {project_key}")
    
    if "warnings" in result and result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
