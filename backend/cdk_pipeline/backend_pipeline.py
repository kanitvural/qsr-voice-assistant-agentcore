from aws_cdk import Stack, aws_codebuild as codebuild, pipelines as pipelines_
from constructs import Construct
from .backend_stage import BackendPipelineStage


class BackendPipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        project_name = self.node.try_get_context("project_name") or "qsr-voice-assistant"
        pipeline_name = f"{project_name}-backend-pipeline-{self.account}"
        notification_email = self.node.try_get_context("notification_email")

        # GitHub connections information
        github_repo = "kanitvural/qsr-voice-assistant-agentcore"
        github_branch = "backend"
        connection_arn = self.node.try_get_context("githubConnectionArn")

        source = pipelines_.CodePipelineSource.connection(
            repo_string=github_repo,
            branch=github_branch,
            connection_arn=connection_arn,
        )

        synth_step = pipelines_.CodeBuildStep(
            "Synth",
            input=source,
            commands=[
                "npm install -g aws-cdk",
                "pip install -r requirements.txt",
                "cdk synth --context @aws-cdk/core:bootstrapQualifier=backend",
            ],
            build_environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2023_STANDARD_3_0,
                compute_type=codebuild.ComputeType.SMALL,
                privileged=True,
            )
        )

        # Create the CodePipeline
        pipeline = pipelines_.CodePipeline(
            self,
            id="BackendPipeline",
            pipeline_name=pipeline_name,
            synth=synth_step,
            asset_publishing_code_build_defaults=pipelines_.CodeBuildOptions(
                build_environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2023_STANDARD_3_0,
                    compute_type=codebuild.ComputeType.SMALL,
                    privileged=True,
                )
            ),
            docker_enabled_for_synth=True,
        )

        backend_stage = BackendPipelineStage(
            self,
            id="BackendPipelineStage",
            project_name=project_name,
            notification_email=notification_email,
        )

        pipeline.add_stage(backend_stage)
