"""
Cognito Post-Confirmation Lambda Trigger

Automatically assigns a unique customerId to newly confirmed users.
This is required because the agent backend reads custom:customerId
from Cognito to identify the customer in DynamoDB.

Trigger Type: Post Confirmation
"""
import uuid
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_client = boto3.client('cognito-idp')


def handler(event, context):
    """
    Post-confirmation trigger handler.
    
    Assigns a UUID-based customerId to the user's custom:customerId attribute
    after successful email verification (ConfirmSignUp).
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        The event object (required by Cognito triggers)
    """
    logger.info(f"Post-confirmation trigger fired: {event}")
    
    trigger_source = event.get('triggerSource', '')
    
    # Only run on PostConfirmation_ConfirmSignUp (not PostConfirmation_ConfirmForgotPassword)
    if trigger_source != 'PostConfirmation_ConfirmSignUp':
        logger.info(f"Skipping trigger for source: {trigger_source}")
        return event
    
    user_pool_id = event['userPoolId']
    username = event['userName']
    
    # Generate a unique customer ID
    customer_id = f"cust-{uuid.uuid4().hex[:12]}"
    
    try:
        cognito_client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'custom:customerId',
                    'Value': customer_id
                }
            ]
        )
        logger.info(f"✅ Assigned customerId '{customer_id}' to user '{username}'")
        
    except ClientError as e:
        logger.error(f"❌ Failed to assign customerId: {e}")
        # Don't raise - let the user confirmation succeed even if this fails
        # The customerId can be assigned later via admin action
    
    return event
