import boto3
import sys

def get_cloudfront_url():
    print("🔍 Fetching QSR Voice Assistant URL from AWS...")
    
    # Using the region defined for this project (usually us-east-1 for CloudFront edge stuff, or dynamic)
    # If the user's AWS config has a default region, boto3 will pick it up.
    # But we can try 'us-east-1' specifically since CloudFront is global and pipelines usually deploy to a primary region.
    client = boto3.client('cloudformation', region_name='us-east-1')
    
    try:
        # Instead of guessing the Pipeline's dynamically generated Stack name, 
        # we can directly query CloudFormation Exports because our S3CloudfrontStack
        # explicitly exports "QSRFrontendUrl".
        paginator = client.get_paginator('list_exports')
        for page in paginator.paginate():
            for export in page['Exports']:
                if export['Name'] == 'QSRFrontendUrl':
                    url = export['Value']
                    print("✅ Success! Your QSR Voice Assistant application is live at:")
                    print(f"🔗 {url}")
                    return
                    
        print("❌ Could not find 'QSRFrontendUrl' in the stack exports.")
        print("Make sure 'make deploy env=frontend' has finished successfully and the pipeline has completed.")
    except Exception as e:
        print(f"❌ Error fetching stack exports: {e}")

if __name__ == "__main__":
    get_cloudfront_url()
