#!/usr/bin/env python3
import subprocess
import json
import tempfile
import os
import re

class GoLinter:
    """Handles Go code linting using multiple tools."""

    def __init__(self):
        # Check if Go is installed
        try:
            subprocess.run(["go", "version"], check=True, capture_output=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("Warning: Go is not installed or not in PATH. Linting functionality will be limited.")
    
    def _write_temp_file(self, code, filename="temp.go"):
        """Write code to a temporary file."""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, "w") as f:
            f.write(code)
        
        return file_path, temp_dir
    
    def run_golint(self, code, filename="temp.go"):
        """Run golint on Go code."""
        try:
            # Create temporary file
            file_path, temp_dir = self._write_temp_file(code, filename)
            
            # Install golint if needed
            try:
                subprocess.run(["golint", "-h"], check=True, capture_output=True, stderr=subprocess.DEVNULL)
            except (subprocess.SubprocessError, FileNotFoundError):
                print("Installing golint...")
                subprocess.run(["go", "install", "golang.org/x/lint/golint@latest"], check=True)
            
            # Run golint
            result = subprocess.run(
                ["golint", file_path], 
                capture_output=True, 
                text=True,
                check=False
            )
            
            return result.stdout.strip() if result.stdout else ""
            
        except Exception as e:
            return f"Error running golint: {str(e)}"
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                subprocess.run(["rm", "-rf", temp_dir], check=False)
    
    def run_go_vet(self, code, filename="temp.go"):
        """Run go vet on Go code."""
        try:
            # Create temporary file in a proper Go module structure
            temp_dir = tempfile.mkdtemp()
            mod_path = os.path.join(temp_dir, "go.mod")
            file_path = os.path.join(temp_dir, filename)
            
            # Initialize Go module
            with open(mod_path, "w") as f:
                f.write("module tempreview\n\ngo 1.19\n")
                
            # Write Go code
            with open(file_path, "w") as f:
                f.write(code)
            
            # Run go vet
            result = subprocess.run(
                ["go", "vet", "./..."], 
                cwd=temp_dir,
                capture_output=True, 
                text=True,
                check=False
            )
            
            return result.stderr.strip() if result.stderr else ""
            
        except Exception as e:
            return f"Error running go vet: {str(e)}"
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                subprocess.run(["rm", "-rf", temp_dir], check=False)
    
    def run_staticcheck(self, code, filename="temp.go"):
        """Run staticcheck on Go code."""
        try:
            # Create temporary file with proper Go module
            temp_dir = tempfile.mkdtemp()
            mod_path = os.path.join(temp_dir, "go.mod")
            file_path = os.path.join(temp_dir, filename)
            
            # Initialize Go module
            with open(mod_path, "w") as f:
                f.write("module tempreview\n\ngo 1.19\n")
                
            # Write Go code
            with open(file_path, "w") as f:
                f.write(code)
            
            # Check if staticcheck is installed
            try:
                subprocess.run(["staticcheck", "-h"], check=True, capture_output=True, stderr=subprocess.DEVNULL)
            except (subprocess.SubprocessError, FileNotFoundError):
                print("Installing staticcheck...")
                subprocess.run(["go", "install", "honnef.co/go/tools/cmd/staticcheck@latest"], check=True)
            
            # Run staticcheck
            result = subprocess.run(
                ["staticcheck", "./..."], 
                cwd=temp_dir,
                capture_output=True, 
                text=True,
                check=False
            )
            
            return result.stdout.strip() if result.stdout else ""
            
        except Exception as e:
            return f"Error running staticcheck: {str(e)}"
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                subprocess.run(["rm", "-rf", temp_dir], check=False)
    
    def lint_go_code(self, code, filename="temp.go"):
        """Run multiple linters on Go code and aggregate results."""
        results = {
            "golint": self.run_golint(code, filename),
            "go_vet": self.run_go_vet(code, filename),
            "staticcheck": self.run_staticcheck(code, filename)
        }
        
        # Format results as markdown
        markdown = "## Linting Results\n\n"
        
        for linter, output in results.items():
            markdown += f"### {linter.replace('_', ' ').title()}\n\n"
            if output:
                markdown += "```\n" + output + "\n```\n\n"
            else:
                markdown += "No issues found.\n\n"
        
        return markdown 