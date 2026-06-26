#!/usr/bin/env python3
"""
Generate frontend/.env.local from AWS CloudFormation exports.

This script fetches the CloudFormation exports dynamically during the 
CodeBuild phase, and creates the .env.local file required by Next.js.
It runs from the root of the project.
"""

import boto3
import os
import sys

def generate_env():
    print("🔧 Generating frontend configuration from AWS CloudFormation exports...\n")
    
    try:
        client = boto3.client('cloudformation')
        
        # Paginate through all exports
        exports = {}
        paginator = client.get_paginator('list_exports')
        for page in paginator.paginate():
            for export in page['Exports']:
                exports[export['Name']] = export['Value']

        # Extract required config values based on our backend CDK export names
        config = {
            "NEXT_PUBLIC_USER_POOL_ID": exports.get("QSR-UserPoolId", ""),
            "NEXT_PUBLIC_CLIENT_ID": exports.get("QSR-UserPoolClientId", ""),
            "NEXT_PUBLIC_IDENTITY_POOL_ID": exports.get("QSR-IdentityPoolId", ""),
            "NEXT_PUBLIC_REGION": boto3.session.Session().region_name or os.environ.get("AWS_REGION", "us-east-1"),
            "NEXT_PUBLIC_WEBSOCKET_URL": exports.get("QSRWebSocketEndpointUrl", ""),
            "NEXT_PUBLIC_RUNTIME_ARN": exports.get("QSRAgentRuntimeArn", ""),
            "NEXT_PUBLIC_MAP_NAME": exports.get("QSR-MapName", "QSRRestaurantMap"),
            "NEXT_PUBLIC_PLACE_INDEX_NAME": exports.get("QSR-PlaceIndexName", "QSRRestaurantIndex")
        }

        # Validate
        missing = [k for k, v in config.items() if not v]
        if missing:
            print("❌ Error: Missing required configuration values from CloudFormation exports:")
            for m in missing:
                print(f"   - {m}")
            print("\nPlease ensure the backend stacks are deployed and exporting these values.")
            sys.exit(1)

        # Generate .env.local content
        env_content = "# Auto-generated from CloudFormation Exports - DO NOT COMMIT\n"
        for key, value in config.items():
            env_content += f"{key}={value}\n"

        # Write to frontend/qsr-app/.env.local 
        # Script is in frontend/scripts/generate_frontend_env.py
        # project_root is frontend/
        frontend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file_path = os.path.join(frontend_root, "qsr-app", ".env.local")
        
        # Ensure the directory exists just in case
        os.makedirs(os.path.dirname(env_file_path), exist_ok=True)
        
        with open(env_file_path, "w") as f:
            f.write(env_content)

        print("✅ Configuration generated successfully!")
        print(f"   File: {env_file_path}\n")
        print("📋 Configuration values:")
        for k, v in config.items():
            print(f"   {k.replace('NEXT_PUBLIC_', '')}: {v}")

    except Exception as e:
        print(f"❌ Error generating configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    generate_env()
