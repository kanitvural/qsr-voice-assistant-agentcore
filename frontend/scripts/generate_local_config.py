#!/usr/bin/env python3
"""
Generate frontend/qsr-app/public/config.json from AWS CloudFormation exports.

This script is exclusively for LOCAL DEVELOPMENT. 
It fetches the CloudFormation exports dynamically and creates the config.json 
file required by the Next.js frontend to connect to the real AWS backend.
"""

import boto3
import os
import sys
import json

def generate_local_config():
    print("🔧 Generating local config.json from AWS CloudFormation exports...\n")
    
    try:
        # Connect to AWS explicitly in us-east-1 since the CDK backend is anchored there
        client = boto3.client('cloudformation', region_name='us-east-1')
        
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
            "NEXT_PUBLIC_REGION": "us-east-1",  # Hardcoded because backend stacks are explicitly deployed in us-east-1
            "NEXT_PUBLIC_WEBSOCKET_URL": exports.get("QSRWebSocketEndpointUrl", ""),
            "NEXT_PUBLIC_RUNTIME_ARN": exports.get("QSRAgentRuntimeArn", "")
        }

        # Check for missing values
        missing = [k for k, v in config.items() if not v]
        if missing:
            print("❌ Error: Missing required configuration values from CloudFormation exports:")
            for m in missing:
                print(f"   - {m}")
            print("\nPlease ensure the backend stacks are deployed in your current AWS profile/region.")
            print("Hint: Check your AWS_REGION or run 'aws configure'.")
            sys.exit(1)

        # Write to frontend/qsr-app/public/config.json 
        frontend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file_path = os.path.join(frontend_root, "qsr-app", "public", "config.json")
        
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        
        with open(config_file_path, "w") as f:
            json.dump(config, f, indent=2)

        print("✅ Local configuration generated successfully!")
        print(f"   File: {config_file_path}\n")
        print("📋 Configuration values:")
        for k, v in config.items():
            print(f"   {k}: {v}")

    except Exception as e:
        print(f"❌ Error generating configuration: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    generate_local_config()
