import json
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_iam as iam,
    aws_bedrockagentcore as agentcore,
    aws_ecr_assets as ecr_assets
)
from constructs import Construct

class AgentCoreStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, api_gateway, user_pool, app_client, cognito_domain_url, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------
        # AgentCore: Gateway with API Gateway Target
        # ------------------------------------------------------------------
        gateway = agentcore.Gateway(
            self, "QSRGateway",
            gateway_name="qsr-ordering-gateway",
            authorizer_configuration=agentcore.GatewayAuthorizer.using_aws_iam(),
            exception_level=agentcore.GatewayExceptionLevel.DEBUG,
            description="QSR Ordering System - MCP Gateway exposing backend APIs as tools"
        )

        api_gateway_target = gateway.add_api_gateway_target(
            "QSR-ApiGatewayTarget",
            rest_api=api_gateway,
            api_gateway_tool_configuration=agentcore.ApiGatewayToolConfiguration(
                tool_filters=[
                    agentcore.ApiGatewayToolFilter(
                        filter_path="/*",
                        methods=[
                            agentcore.ApiGatewayHttpMethod.GET,
                            agentcore.ApiGatewayHttpMethod.POST,
                            agentcore.ApiGatewayHttpMethod.PUT,
                            agentcore.ApiGatewayHttpMethod.DELETE
                        ]
                    )
                ]
            )
        )

        # ------------------------------------------------------------------
        # AgentCore: Build Docker Image for Runtime
        # ------------------------------------------------------------------
        import os
        agent_image = ecr_assets.DockerImageAsset(
            self, "QSRAgentImage",
            directory=os.path.join(os.path.dirname(__file__), '..', 'agent_core'),
            platform=ecr_assets.Platform.LINUX_ARM64
        )

        # ------------------------------------------------------------------
        # AgentCore: Runtime Role
        # ------------------------------------------------------------------
        runtime_role = iam.Role(
            self, "QSRAgentRuntimeRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("bedrock-agentcore.amazonaws.com")
            )
        )
        runtime_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess"))
        runtime_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock-agentcore:InvokeGateway"],
            resources=[gateway.gateway_arn]
        ))
        runtime_role.add_to_policy(iam.PolicyStatement(
            actions=["cognito-idp:DescribeUserPoolClient"],
            resources=[user_pool.user_pool_arn]
        ))
        
        # Grant full read access to ECR so Bedrock AgentCore can validate and pull the Docker image
        runtime_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"))

        # ------------------------------------------------------------------
        # AgentCore: Runtime (L1 construct since we need protocolConfiguration="HTTP")
        # ------------------------------------------------------------------
        runtime = agentcore.CfnRuntime(
            self, "QSRAgentRuntime",
            agent_runtime_name="qsr_ordering_agent_runtime",
            description="QSR ordering agent with Nova Sonic v2 and WebSocket protocol",
            role_arn=runtime_role.role_arn,
            agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=agentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=agent_image.image_uri
                )
            ),
            network_configuration=agentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC"
            ),
            protocol_configuration="HTTP",
            environment_variables={
                "LOG_LEVEL": "INFO",
                "AGENTCORE_GATEWAY_URL": gateway.gateway_url,
                "COMPANY_NAME": "Burger Palace",
                "IMAGE_VERSION": "1.0",
                "COGNITO_DOMAIN": cognito_domain_url,
                "COGNITO_CLIENT_ID": app_client.user_pool_client_id,
                "COGNITO_USER_POOL_ID": user_pool.user_pool_id
            }
        )

        # ------------------------------------------------------------------
        # Outputs
        # ------------------------------------------------------------------
        CfnOutput(self, "GatewayEndpoint", value=gateway.gateway_url, export_name="QSRGatewayEndpoint")
        CfnOutput(self, "AgentRuntimeArn", value=runtime.attr_agent_runtime_arn, export_name="QSRAgentRuntimeArn")
        CfnOutput(self, "WebSocketEndpointUrl", value=f"wss://{runtime.agent_runtime_name}.agentcore.bedrock.{self.region}.amazonaws.com", export_name="QSRWebSocketEndpointUrl")
