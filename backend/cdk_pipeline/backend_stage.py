from aws_cdk import Stage
from constructs import Construct

from backend.stacks.dynamodb_stack import DynamoDBStack
from backend.stacks.location_stack import LocationStack
from backend.stacks.cognito_stack import CognitoStack
from backend.stacks.lambda_stack import LambdaStack
from backend.stacks.api_gateway_stack import ApiGatewayStack
from backend.stacks.agentcore_stack import AgentCoreStack

class BackendPipelineStage(Stage):
    def __init__(self, scope: Construct, id: str, project_name: str, notification_email: str = None, **kwargs):
        super().__init__(scope, id, **kwargs)

        dynamodb_stack = DynamoDBStack(self, f"{project_name}-DynamoDBStack")
        location_stack = LocationStack(self, f"{project_name}-LocationStack")
        
        # LambdaStack must be created before CognitoStack because CognitoStack
        # needs the post_confirmation Lambda function as a trigger.
        lambda_stack = LambdaStack(self, f"{project_name}-LambdaStack", dynamodb_stack, location_stack)

        cognito_stack = CognitoStack(
            self, f"{project_name}-CognitoStack",
            api_gateway_arn="*",
            post_confirmation_lambda=lambda_stack.post_confirmation
        )
        
        api_gateway_stack = ApiGatewayStack(self, f"{project_name}-ApiGatewayStack", cognito_stack, lambda_stack)
        
        agentcore_stack = AgentCoreStack(
            self, f"{project_name}-AgentCoreStack",
            api_gateway=api_gateway_stack.api,
            user_pool=cognito_stack.user_pool,
            app_client=cognito_stack.user_pool_client,
            cognito_domain_url="" # Not strictly needed
        )

