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

        # For the frontend we usually build Next.js, but since we are just putting the out folder to S3
        # the CDK synth step handles the CDK generation. Next.js build will happen here or inside the stack.
        synth_step = pipelines_.ShellStep(
            "Synth",
            input=source,
            commands=[
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

        bucket_name = f"{project_name}-frontend-{self.account}-{self.region}"

        deploy_frontend_app = pipelines_.CodeBuildStep(
            "DeployFrontendApp",
            input=source,
            install_commands=[
                "echo '📦 Installing Node.js and npm versions...' ",
                "node -v",
                "npm -v",
                "echo '📦 Installing Python dependencies...' ",
                "pip install boto3",
            ],
            commands=[
                "echo '📦 Generating frontend environment configuration...'",
                "python frontend/scripts/generate_frontend_env.py",
                "echo '📦 Navigating to frontend project...'",
                "cd frontend/qsr-app",
                "echo '📦 Installing frontend dependencies...'",
                "npm ci",
                "echo '🏗 Building Next.js project...'",
                "npm run build",
                "echo '📤 Syncing out/ folder to S3...'",
                f"aws s3 rm s3://{bucket_name} --recursive",
                f"aws s3 cp out/ s3://{bucket_name} --recursive",
                # Note: CloudFront invalidation could be added here if needed
            ],
            partial_build_spec=codebuild.BuildSpec.from_object(
                {
                    "phases": {
                        "install": {
                            "runtime-versions": {
                                "nodejs": "22",
                            },
                        },
                    },
                }
            ),
            build_environment=codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL,
                build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                privileged=True,
            ),
            role_policy_statements=[
                iam.PolicyStatement(
                    actions=[
                        "s3:ListBucket",
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                    ],
                    resources=[
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*",
                    ],
                ),
                iam.PolicyStatement(
                    actions=[
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["cloudfront:*"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=["cloudformation:ListExports"],
                    resources=["*"],
                ),
            ],
        )
        
        frontend_infra_deploy.add_post(deploy_frontend_app)
