#!/usr/bin/env python3
import os
import sys
import argparse
from github import Github
from reviewer import review_go_code

def get_go_files_from_pr(repo_name, pr_number, github_token):
    """Get all Go files modified in a PR."""
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    go_files = {}
    for file in pr.get_files():
        if file.filename.endswith('.go'):
            go_files[file.filename] = file.patch
    
    return go_files

def post_review_comment(repo_name, pr_number, comments, github_token):
    """Post review comments to the PR."""
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    # Post a comment with all reviews
    pr.create_issue_comment(comments)
    print(f"Posted review comments to PR #{pr_number}")

def main():
    parser = argparse.ArgumentParser(description='Review Go code in GitHub PRs')
    parser.add_argument('--repo', required=True, help='GitHub repository in format owner/repo')
    parser.add_argument('--pr', required=True, type=int, help='Pull request number')
    parser.add_argument('--token', help='GitHub token (can also be provided via GITHUB_TOKEN env var)')
    
    args = parser.parse_args()
    
    # Get GitHub token
    github_token = args.token or os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Error: GitHub token not provided. Use --token or set GITHUB_TOKEN env var.")
        sys.exit(1)
    
    # Get modified Go files from PR
    go_files = get_go_files_from_pr(args.repo, args.pr, github_token)
    
    if not go_files:
        print("No Go files found in this PR.")
        return
    
    # Review each Go file
    all_comments = f"# 🤖 Go Code Review Bot\n\nReviewed {len(go_files)} Go files.\n\n"
    
    for filename, code in go_files.items():
        print(f"Reviewing {filename}...")
        review = review_go_code(code)
        
        file_comments = f"## {filename}\n\n{review}\n\n"
        all_comments += file_comments
    
    # Post review comments
    post_review_comment(args.repo, args.pr, all_comments, github_token)

if __name__ == "__main__":
    main() 