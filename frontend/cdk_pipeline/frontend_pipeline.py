from aws_cdk import Stack, pipelines as pipelines_, aws_codebuild as codebuild, aws_iam as iam
from constructs import Construct
from .frontend_stage import FrontendPipelineStage


class FrontendPipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        project_name = self.node.try_get_context("project_name") or "qsr-voice-assistant"
        pipeline_name = f"{project_name}-frontend-pipeline-{self.account}"

        # GitHub connections information
        github_repo = "kanitvural/qsr-voice-assistant-agentcore"
        github_branch = "frontend"
        connection_arn = self.node.try_get_context("githubConnectionArn")

        source = pipelines_.CodePipelineSource.connection(
            repo_string=github_repo,
            branch=github_branch,
            connection_arn=connection_arn,
        )

        synth_step = pipelines_.ShellStep(
            "Synth",
            input=source,
            commands=[
                "echo '📦 Installing Node.js dependencies...'",
                "cd frontend/qsr-app && npm ci && npm run build && cd ../..",
                "echo '📦 Synthesizing CDK...'",
                "npm install -g aws-cdk",
                "pip install -r requirements.txt",
                "cdk synth --context @aws-cdk/core:bootstrapQualifier=frontend",
            ],
        )

        # Create the CodePipeline
        pipeline = pipelines_.CodePipeline(
            self,
            id="FrontendPipeline",
            pipeline_name=pipeline_name,
            synth=synth_step,
        )

        frontend_stage = FrontendPipelineStage(
            self,
            id="FrontendPipelineStage",
            project_name=project_name,
        )

        # Add the FrontendStage to the pipeline
        frontend_infra_deploy = pipeline.add_stage(frontend_stage)

        # Remove deploy_frontend_app because BucketDeployment handles it natively in the Stack
