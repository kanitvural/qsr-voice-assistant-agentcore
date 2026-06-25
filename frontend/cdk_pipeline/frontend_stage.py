from aws_cdk import Stage
from constructs import Construct

from frontend.stacks.s3_cloudfront_stack import S3CloudfrontStack

class FrontendPipelineStage(Stage):
    def __init__(self, scope: Construct, id: str, project_name: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        s3_cloudfront_stack = S3CloudfrontStack(self, f"{project_name}-S3CloudfrontStack")
