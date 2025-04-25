#!/usr/bin/env python3
import os
import sys
import argparse
import re
import base64
import json
import time
from github import Github, GithubException
from reviewer import review_go_code
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# Constants
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

def get_go_files_from_pr(repo_name, pr_number, github_token, max_files=None):
    """Get all Go files modified in a PR with proper diff information."""
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    go_files = {}
    file_count = 0
    
    # Get list of files modified in PR
    for file in pr.get_files():
        if file.filename.endswith('.go'):
            # Only process added or modified files (skip deleted)
            if file.status in ['added', 'modified']:
                # Check if we've hit the max files limit
                if max_files and file_count >= max_files:
                    print(f"Reached maximum file limit ({max_files}), skipping remaining files")
                    break
                
                # Get the full content of the file
                try:
                    file_content = repo.get_contents(file.filename, ref=pr.head.ref).decoded_content.decode('utf-8')
                except Exception as e:
                    print(f"Warning: Could not get content for {file.filename}: {str(e)}")
                    file_content = None
                
                # Parse diff to get line mapping information
                line_map = parse_diff_for_line_mapping(file.patch)
                
                go_files[file.filename] = {
                    'patch': file.patch,
                    'content': file_content,
                    'line_map': line_map,
                    'file_obj': file
                }
                file_count += 1
    
    return go_files, pr

def parse_diff_for_line_mapping(diff):
    """
    Parse git diff to map source line numbers to position in the diff.
    Returns a dictionary mapping source line numbers to positions in the diff.
    """
    if not diff:
        return {}
    
    line_map = {}
    position = 0
    source_line = 0
    
    for line in diff.split('\n'):
        position += 1
        
        # Skip diff header lines
        if line.startswith('@@'):
            # Extract the starting line number from the diff header
            # Format is like @@ -1,7 +1,7 @@
            match = re.search(r'\+(\d+)', line)
            if match:
                source_line = int(match.group(1)) - 1
            continue
        
        # Track actual file lines (skip removed lines)
        if not line.startswith('-'):
            source_line += 1
            line_map[source_line] = position
    
    return line_map

def parse_review_for_inline_comments(review_text):
    """Parse the LLM review output to extract inline comments.
    
    Format expected: 
    - Line X: Comment about this line
    - Lines X-Y: Comment about these lines
    - Line X: Comment about this line
      Suggested fix:
      ```go
      // Suggested code
      ```
    """
    comments = []
    
    # Look for patterns like "Line X:" or "Lines X-Y:"
    line_patterns = [
        r'(?:Line|line)\s+(\d+)\s*:\s*(.*?)(?=(?:Line|line)|$)',
        r'(?:Lines|lines)\s+(\d+)-(\d+)\s*:\s*(.*?)(?=(?:Line|line)|$)'
    ]
    
    for pattern in line_patterns:
        if "Lines" in pattern or "lines" in pattern:
            # Handle range of lines
            matches = re.finditer(pattern, review_text, re.DOTALL)
            for match in matches:
                start_line = int(match.group(1))
                end_line = int(match.group(2))
                comment_text = match.group(3).strip()
                
                # Extract code suggestion if present
                suggestion = extract_code_suggestion(comment_text)
                
                if comment_text:
                    comments.append({
                        'start_line': start_line,
                        'end_line': end_line,
                        'body': comment_text,
                        'has_suggestion': suggestion is not None,
                        'suggestion': suggestion
                    })
        else:
            # Handle single line
            matches = re.finditer(pattern, review_text, re.DOTALL)
            for match in matches:
                line_num = int(match.group(1))
                comment_text = match.group(2).strip()
                
                # Extract code suggestion if present
                suggestion = extract_code_suggestion(comment_text)
                
                if comment_text:
                    comments.append({
                        'start_line': line_num,
                        'end_line': line_num,
                        'body': comment_text,
                        'has_suggestion': suggestion is not None,
                        'suggestion': suggestion
                    })
    
    # Also look for bullet points that might contain line numbers
    bullet_pattern = r'[-\*]\s+(.*?)(?=[-\*]|$)'
    bullet_matches = re.finditer(bullet_pattern, review_text, re.DOTALL)
    
    for match in bullet_matches:
        bullet_text = match.group(1).strip()
        # Check if the bullet point contains line numbers
        line_num_match = re.search(r'(?:Line|line)\s+(\d+)', bullet_text)
        if line_num_match:
            line_num = int(line_num_match.group(1))
            
            # Extract code suggestion if present
            suggestion = extract_code_suggestion(bullet_text)
            
            comments.append({
                'start_line': line_num,
                'end_line': line_num,
                'body': bullet_text,
                'has_suggestion': suggestion is not None,
                'suggestion': suggestion
            })
    
    # If no structured comments found, use the whole review as a general comment
    if not comments and review_text.strip():
        comments.append({
            'start_line': None,
            'end_line': None,
            'body': "General feedback: " + review_text.strip(),
            'has_suggestion': False,
            'suggestion': None
        })
    
    return comments

def extract_code_suggestion(comment_text):
    """Extract code suggestion from comment text if present.
    
    Format expected:
    Suggested fix:
    ```go
    // Suggested code
    ```
    """
    if not comment_text:
        return None
        
    # Look for code blocks after "Suggested fix:" or similar phrases
    suggestion_pattern = r'(?:Suggested fix:|Suggested code:|Fix:|Code suggestion:)\s*```(?:go)?\s*(.*?)```'
    match = re.search(suggestion_pattern, comment_text, re.DOTALL)
    
    if match:
        code = match.group(1).strip()
        # Remove any "go" language specifier that might have been captured
        if code.startswith("go\n"):
            code = code[3:].strip()
        return code
    return None

def post_inline_review_comments(repo_name, pr_number, file_comments, github_token, review_mode="comment", review_event="COMMENT"):
    """Post inline review comments to the PR using accurate position information.
    
    Args:
        repo_name: The GitHub repository name in format owner/repo
        pr_number: The PR number
        file_comments: Dictionary of file comments
        github_token: GitHub API token
        review_mode: Mode to use for review ("comment", "request_changes", or "approve")
        review_event: GitHub review event (COMMENT, REQUEST_CHANGES, APPROVE)
    """
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    # Store comments that couldn't be posted inline
    general_comments = []
    inline_comments_count = 0
    
    # Prepare the review with comments
    comments_for_review = []
    
    for filename, file_data in file_comments.items():
        line_map = file_data.get('line_map', {})
        file_comments_list = file_data.get('comments', [])
        
        for comment in file_comments_list:
            if comment['start_line'] is not None and comment['start_line'] in line_map:
                # We have a valid position in the diff
                diff_position = line_map[comment['start_line']]
                
                # Format comment body with code suggestion if available
                comment_body = ""
                
                # If there's a code suggestion, format it as a GitHub suggestion block
                if comment.get('has_suggestion') and comment.get('suggestion'):
                    # Extract the feedback part (before the suggestion)
                    feedback_part = re.sub(r'Suggested fix:.*', '', comment['body'], flags=re.DOTALL).strip()
                    
                    # Format using GitHub's suggestion syntax
                    # This is the exact format GitHub uses for suggestions that can be committed directly
                    comment_body = f"Line {comment['start_line']}: {feedback_part}\n\n```suggestion\n{comment['suggestion']}\n```"
                else:
                    comment_body = f"Line {comment['start_line']}: {comment['body']}"
                
                # Add to comments for the review
                comments_for_review.append({
                    'path': filename,
                    'position': diff_position,
                    'body': comment_body
                })
                inline_comments_count += 1
            else:
                # If we can't map to a position, add as a general comment
                if comment['start_line'] is not None:
                    line_info = f"(Line {comment['start_line']})"
                else:
                    line_info = ""
                general_comments.append(f"**{filename} {line_info}:** {comment['body']}")
    
    # Create a summary for the review body
    review_body = "# 🤖 Go Code Review Bot\n\n"
    
    if inline_comments_count > 0:
        review_body += f"Found {inline_comments_count} issues to comment on.\n\n"
    
    # Add summary based on review mode
    if review_mode == "request_changes":
        review_body += "⚠️ **Changes requested.** Please address the highlighted issues.\n\n"
    elif review_mode == "approve":
        review_body += "✅ **Code looks good!** Some minor suggestions provided inline.\n\n"
    else:
        review_body += "📝 **Code review completed.** See inline comments for details.\n\n"
    
    # Create the review with all the inline comments
    if comments_for_review:
        for attempt in range(MAX_RETRIES):
            try:
                # Create a review with all comments
                review = pr.create_review(
                    body=review_body,
                    event=review_event,
                    comments=comments_for_review
                )
                print(f"Added {len(comments_for_review)} inline comments to PR #{pr_number}")
                break
            except GithubException as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"Error creating review (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"Failed to create review after {MAX_RETRIES} attempts: {str(e)}")
                    # If the batched review fails, try adding comments one by one
                    add_individual_comments(pr, comments_for_review, general_comments)
            except Exception as e:
                print(f"Unexpected error creating review: {str(e)}")
                # If the batched review fails, try adding comments one by one
                add_individual_comments(pr, comments_for_review, general_comments)
                break
    
    # If we have general comments, add them as a PR comment
    if general_comments:
        general_comment = "# 🤖 Go Code Review Bot - Additional Comments\n\n"
        if inline_comments_count > 0:
            general_comment += f"Added {inline_comments_count} inline comments.\n\n"
        general_comment += "\n\n".join(general_comments)
        
        try:
            pr.create_issue_comment(general_comment)
        except Exception as e:
            print(f"Error posting general comments: {str(e)}")
    elif inline_comments_count == 0:
        try:
            pr.create_issue_comment("# 🤖 Go Code Review Bot\n\nReviewed the code but found no specific issues to comment on.")
        except Exception as e:
            print(f"Error posting 'no issues' comment: {str(e)}")

def add_individual_comments(pr, comments_for_review, general_comments):
    """Add comments individually when batch commenting fails."""
    print("Trying to add comments individually...")
    
    commit_id = None
    try:
        # Get the latest commit ID
        commit_id = pr.get_commits().reversed[0].sha
    except Exception as e:
        print(f"Error getting latest commit: {str(e)}")
        return
    
    success_count = 0
    for comment in comments_for_review:
        try:
            # The body already contains the formatted comment with suggestion if applicable
            pr.create_review_comment(
                body=comment['body'],
                commit_id=commit_id,
                path=comment['path'],
                position=comment['position']
            )
            success_count += 1
        except Exception as e:
            print(f"Error adding individual comment: {str(e)}")
            general_comments.append(f"**{comment['path']}:** {comment['body']}")
    
    print(f"Added {success_count}/{len(comments_for_review)} comments individually")

def load_config(config_file):
    """Load configuration from file."""
    default_config = {
        "max_files": None,
        "review_mode": "comment",  # comment, request_changes, approve
        "review_event": "COMMENT",  # COMMENT, REQUEST_CHANGES, APPROVE
        "severity_threshold": "info"  # info, warning, error
    }
    
    if not os.path.exists(config_file):
        return default_config
        
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            # Update defaults with file values
            default_config.update(config)
        return default_config
    except Exception as e:
        print(f"Error loading config file: {str(e)}")
        return default_config

def main():
    parser = argparse.ArgumentParser(description='Review Go code in GitHub PRs')
    parser.add_argument('--repo', required=True, help='GitHub repository in format owner/repo')
    parser.add_argument('--pr', required=True, type=int, help='Pull request number')
    parser.add_argument('--token', help='GitHub token (can also be provided via GITHUB_TOKEN env var)')
    parser.add_argument('--verbose', action='store_true', help='Print more information during execution')
    parser.add_argument('--config', default='review_config.json', help='Path to configuration file')
    parser.add_argument('--max-files', type=int, help='Maximum number of files to review')
    parser.add_argument('--mode', choices=['comment', 'request_changes', 'approve'], 
                        help='Review mode: comment, request changes, or approve')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Command line args override config file
    if args.max_files is not None:
        config['max_files'] = args.max_files
    if args.mode is not None:
        config['review_mode'] = args.mode
        if args.mode == 'request_changes':
            config['review_event'] = 'REQUEST_CHANGES'
        elif args.mode == 'approve':
            config['review_event'] = 'APPROVE'
    
    # Get GitHub token
    github_token = args.token or os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Error: GitHub token not provided. Use --token or set GITHUB_TOKEN env var.")
        sys.exit(1)
    
    # Get modified Go files from PR
    go_files, pr = get_go_files_from_pr(args.repo, args.pr, github_token, config['max_files'])
    
    if not go_files:
        print("No Go files found in this PR.")
        return
    
    print(f"Found {len(go_files)} Go files to review in PR #{args.pr}")
    
    # Review each Go file
    for filename, file_info in go_files.items():
        print(f"Reviewing {filename}...")
        
        # LLM-based review on the full file content if available, otherwise the patch
        content_to_review = file_info.get('content', file_info.get('patch', ''))
        if not content_to_review:
            print(f"Warning: No content to review for {filename}")
            continue
            
        review = review_go_code(content_to_review)
        
        if args.verbose:
            print(f"Raw review for {filename}:")
            print(review)
            print("-" * 40)
        
        # Parse the review for inline comments
        file_comments = parse_review_for_inline_comments(review)
        go_files[filename]['comments'] = file_comments
    
    # Post inline review comments with the configured mode
    post_inline_review_comments(
        args.repo, 
        args.pr, 
        go_files, 
        github_token,
        review_mode=config['review_mode'],
        review_event=config['review_event']
    )

if __name__ == "__main__":
    main()