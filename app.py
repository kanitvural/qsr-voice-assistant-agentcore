#!/usr/bin/env python3
import os
import aws_cdk as cdk

from backend.cdk_pipeline.backend_pipeline import BackendPipelineStack
from frontend.cdk_pipeline.frontend_pipeline import FrontendPipelineStack

app = cdk.App()

env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region="us-east-1"
)

qualifier = app.node.try_get_context("@aws-cdk/core:bootstrapQualifier")

if qualifier == "backend" or not qualifier:
    # Backend Pipeline Stack
    backend_pipeline_stack = BackendPipelineStack(
        app, "QSRVoiceAssistantBackendPipeline",
        env=env
    )

if qualifier == "frontend" or not qualifier:
    # Frontend Pipeline Stack
    frontend_pipeline_stack = FrontendPipelineStack(
        app, "QSRVoiceAssistantFrontendPipeline",
        env=env
    )

app.synth()
