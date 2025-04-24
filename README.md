# Go Code Reviewer for GitHub PRs

This tool uses LLM to automatically review Go code in GitHub pull requests. It leverages the Llama3.2 model via Ollama to provide actionable feedback on Go code quality, bugs, concurrency issues, performance, and security.

## Features

- **LLM-powered code review** using Llama3.2
- **Inline comments** - places feedback directly on specific lines of code
- **Automated linting** with multiple Go linters
- **GitHub PR integration** - comments directly on PRs
- **GitHub Actions support** - automate reviews on every PR
- **Configurable review modes** - comment, request changes, or approve
- **Error resilience** - retries and fallbacks for API failures

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Ollama from [https://ollama.ai/](https://ollama.ai/)
4. Pull the Llama3.2 model:
   ```
   ollama pull llama3.2
   ```
5. Configure your GitHub token:
   ```
   # Create .env file with your GitHub token
   echo "GITHUB_TOKEN=your_personal_access_token" > .env
   ```

## Usage

### Basic Usage

```bash
# Review a PR with default settings
python github_pr_reviewer.py --repo owner/repo --pr 123

# Review with verbose output
python github_pr_reviewer.py --repo owner/repo --pr 123 --verbose
```

### Advanced Usage

```bash
# Limit the number of files to review
python github_pr_reviewer.py --repo owner/repo --pr 123 --max-files 5

# Request changes instead of just commenting
python github_pr_reviewer.py --repo owner/repo --pr 123 --mode request_changes

# Use custom config file
python github_pr_reviewer.py --repo owner/repo --pr 123 --config my_config.json
```

## Configuration

You can customize the reviewer behavior using a JSON configuration file:

```json
{
    "max_files": 10,
    "review_mode": "comment",
    "review_event": "COMMENT",
    "severity_threshold": "info",
    "ignore_patterns": [
        "vendor/",
        "*/generated/*.go"
    ]
}
```

Configuration options:

| Option | Description | Values |
|--------|-------------|--------|
| max_files | Maximum number of files to review | Number or null |
| review_mode | Review mode | "comment", "request_changes", "approve" |
| review_event | GitHub API event | "COMMENT", "REQUEST_CHANGES", "APPROVE" |
| severity_threshold | Minimum severity level to report | "info", "warning", "error" |
| ignore_patterns | Patterns of files to ignore | Array of glob patterns |

## GitHub Action Integration

Create a `.github/workflows/go-review.yml` file in your repository:

```yaml
name: Go Code Review

on:
  pull_request:
    paths:
      - '**.go'

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Set up Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.19'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Install Ollama
        run: |
          curl -fsSL https://ollama.ai/install.sh | sh
          ollama pull llama3.2
          
      - name: Run Go code reviewer
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python github_pr_reviewer.py --repo ${{ github.repository }} --pr ${{ github.event.pull_request.number }}
```

## Review a Specific File

You can also review individual Go files directly:

```python
from reviewer import review_go_code

# Example Go code
code = """
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
"""

# Get review feedback
review = review_go_code(code)
print(review)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 