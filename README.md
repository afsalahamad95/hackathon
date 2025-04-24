# Go Code Reviewer for GitHub PRs

This tool uses LLM to automatically review Go code in GitHub pull requests. It leverages the Llama3.2 model via Ollama to provide actionable feedback on Go code quality, bugs, concurrency issues, performance, and security.

## Features

- **LLM-powered code review** using Llama3.2
- **Automated linting** with multiple Go linters:
  - golint - for style issues
  - go vet - for potential bugs
  - staticcheck - for advanced static analysis
- **GitHub PR integration** - comments directly on PRs
- **GitHub Actions support** - automate reviews on every PR

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
5. For linting functionality, ensure Go is installed:
   ```
   # Install Go (if not already installed)
   # For MacOS with Homebrew
   brew install go
   
   # For Ubuntu/Debian
   sudo apt-get install golang-go
   ```

## Usage

### Review Go code directly

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

### Lint Go code directly

```python
from linter import GoLinter

# Initialize linter
linter = GoLinter()

# Example Go code
code = """
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
"""

# Get linting results
lint_results = linter.lint_go_code(code)
print(lint_results)
```

### Review Go code in GitHub PRs

```bash
# Set your GitHub token
export GITHUB_TOKEN=your_github_token

# Run the PR reviewer with all features
python github_pr_reviewer.py --repo owner/repo --pr 123

# Skip linting if Go is not installed
python github_pr_reviewer.py --repo owner/repo --pr 123 --skip-lint

# Use only LLM review, no linting
python github_pr_reviewer.py --repo owner/repo --pr 123 --llm-only
```

You can also provide the token via the command line:
```bash
python github_pr_reviewer.py --repo owner/repo --pr 123 --token your_github_token
```

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

## Configuration

You can customize the review prompt in `reviewer.py` to focus on specific aspects of Go code that are important for your project. 