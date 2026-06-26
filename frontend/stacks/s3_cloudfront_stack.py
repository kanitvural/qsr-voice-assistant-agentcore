import os
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3deploy,
    RemovalPolicy,
    CfnOutput,
    Duration,
    Fn
)
from constructs import Construct

class S3CloudfrontStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ------------------------------------------------------------------
        # Frontend S3 Bucket (Private, accessed only by CloudFront OAC)
        # ------------------------------------------------------------------
        project_name = self.node.try_get_context("project_name") or "qsr-voice-assistant"
        site_bucket = s3.Bucket(
            self, "QSRFrontendBucket",
            bucket_name=f"{project_name}-frontend-{self.account}-{self.region}",
            website_index_document="index.html",
            website_error_document="index.html", # For SPA routing
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # ------------------------------------------------------------------
        # CloudFront Origin Access Control (OAC)
        # ------------------------------------------------------------------
        oac = cloudfront.S3OriginAccessControl(self, "QSRFrontendOAC")

        # ------------------------------------------------------------------
        # CloudFront Distribution
        # ------------------------------------------------------------------
        distribution = cloudfront.Distribution(
            self, "QSRFrontendDistribution",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    site_bucket,
                    origin_access_control=oac
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD,
                compress=True,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.minutes(30)
                )
            ]
        )

        # ------------------------------------------------------------------
        # Deploy App files and dynamic config.json
        # ------------------------------------------------------------------
        s3deploy.BucketDeployment(
            self,
            "DeployFrontendApp",
            sources=[
                s3deploy.Source.asset("frontend/qsr-app/out"),
                s3deploy.Source.json_data("config.json", {
                    "NEXT_PUBLIC_REGION": self.region,
                    "NEXT_PUBLIC_USER_POOL_ID": Fn.import_value("QSR-UserPoolId"),
                    "NEXT_PUBLIC_CLIENT_ID": Fn.import_value("QSR-UserPoolClientId"),
                    "NEXT_PUBLIC_IDENTITY_POOL_ID": Fn.import_value("QSR-IdentityPoolId"),
                    "NEXT_PUBLIC_WEBSOCKET_URL": Fn.import_value("QSRWebSocketEndpointUrl"),
                    "NEXT_PUBLIC_RUNTIME_ARN": Fn.import_value("QSRAgentRuntimeArn"),
                }),
            ],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # ------------------------------------------------------------------
        # Outputs
        # ------------------------------------------------------------------
        CfnOutput(self, "CloudFrontURL", value=f"https://{distribution.distribution_domain_name}", export_name="QSRFrontendUrl")
        CfnOutput(self, "BucketName", value=site_bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=distribution.distribution_id)
