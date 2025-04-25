from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import os
from github_pr_reviewer import main as review_pr
import dotenv

dotenv.load_dotenv()

app = Flask(__name__)

# Get webhook secret from environment variable
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

def verify_webhook_signature(payload, signature):
    """Verify the webhook signature from GitHub."""
    if not WEBHOOK_SECRET:
        return False
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    # Get the signature from the request headers
    signature = request.headers.get('X-Hub-Signature-256')
    if not signature:
        return jsonify({'error': 'No signature provided'}), 401
    
    # Verify the webhook signature
    if not verify_webhook_signature(request.get_data(), signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse the webhook payload
    payload = request.json
    
    # Check if this is a PR event
    if request.headers.get('X-GitHub-Event') == 'pull_request':
        action = payload.get('action')
        
        # Only process when PR is opened or reopened
        if action in ['opened', 'reopened']:
            pr = payload.get('pull_request')
            repo = payload.get('repository')
            
            if pr and repo:
                # Extract necessary information
                repo_name = repo.get('full_name')
                pr_number = pr.get('number')
                
                # Trigger the PR review
                try:
                    review_pr(repo_name, pr_number)
                    return jsonify({'message': 'PR review triggered successfully'}), 200
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
    
    return jsonify({'message': 'Webhook received but no action taken'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=12000) 