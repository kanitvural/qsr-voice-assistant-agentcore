from aws_cdk import (
    Stack,
    aws_cognito as cognito,
    aws_iam as iam,
    CfnParameter,
    Names,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct

class CognitoStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, api_gateway_arn: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Parameters for initial user creation
        user_email = CfnParameter(
            self, "UserEmail",
            type="String",
            description="Email address for initial AppUser creation",
            constraint_description="Must be a valid email address",
            default="admin@example.com"
        )

        user_name = CfnParameter(
            self, "UserName",
            type="String",
            description="Full name for initial AppUser creation",
            constraint_description="Must be a valid name",
            default="Admin User"
        )

        # Auto-generate unique customer ID for the initial user
        unique_id = Names.unique_id(self).lower()[:8]
        customer_id = f"cust-{unique_id}"

        # Email Body Template
        email_body = """
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:32px 40px;text-align:center;">
              <div style="font-size:28px;margin-bottom:8px;">🎙️ 🍔 🍟 🍗 🥤 📍</div>
              <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:600;">QSR Voice Ordering</h1>
              <p style="color:#a0aec0;margin:6px 0 0;font-size:13px;">AI-Powered · Voice-First · Location-Aware</p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <p style="color:#2d3748;font-size:15px;line-height:1.6;margin:0 0 20px;">
                Hello <strong>{username}</strong>, welcome aboard!
              </p>
              <p style="color:#4a5568;font-size:14px;line-height:1.6;margin:0 0 24px;">
                Your account has been created. Use the credentials below to sign in and start testing the voice ordering experience.
              </p>
              <!-- Credentials Box -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:24px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                      <tr>
                        <td style="color:#718096;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;padding-bottom:4px;">Username</td>
                      </tr>
                      <tr>
                        <td style="color:#1a202c;font-size:16px;font-weight:600;font-family:'Courier New',monospace;padding-bottom:16px;">{username}</td>
                      </tr>
                      <tr>
                        <td style="color:#718096;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;padding-bottom:4px;">Temporary Password</td>
                      </tr>
                      <tr>
                        <td style="color:#1a202c;font-size:16px;font-weight:600;font-family:'Courier New',monospace;">{####}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
              <!-- Notice -->
              <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#fffbeb;border-left:4px solid #f59e0b;border-radius:0 6px 6px 0;margin-bottom:24px;">
                <tr>
                  <td style="padding:12px 16px;">
                    <p style="color:#92400e;font-size:13px;margin:0;line-height:1.5;">
                      ⚠️ Copy the password exactly as shown. You will be asked to set a new password on first sign-in.
                    </p>
                  </td>
                </tr>
              </table>
              <p style="color:#a0aec0;font-size:12px;margin:0;text-align:center;">
                This is an automated message from the QSR Voice Ordering System.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

        # Create User Pool
        self.user_pool = cognito.UserPool(
            self, "QSRUserPool",
            user_pool_name="QSR-UserPool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True, username=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            user_invitation=cognito.UserInvitationConfig(
                email_subject="🎙️ QSR Voice Ordering — Your Account is Ready",
                email_body=email_body
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
                fullname=cognito.StandardAttribute(required=True, mutable=True)
            ),
            custom_attributes={
                "customerId": cognito.StringAttribute(mutable=False)
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create User Pool Client
        self.user_pool_client = self.user_pool.add_client(
            "QSRWebClient",
            user_pool_client_name="QSR-WebClient",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False,
            prevent_user_existence_errors=True
        )

        # Create Identity Pool
        self.identity_pool = cognito.CfnIdentityPool(
            self, "QSRIdentityPool",
            identity_pool_name="QSR-IdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=self.user_pool_client.user_pool_client_id,
                    provider_name=self.user_pool.user_pool_provider_name
                )
            ]
        )

        # Create IAM role for authenticated users
        self.authenticated_role = iam.Role(
            self, "CognitoAuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                conditions={
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity"
            ),
            description="Role for authenticated Cognito users with AgentCore access"
        )

        # Add AgentCore permissions
        self.authenticated_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:InvokeAgent",
                    "bedrock-agentcore:InvokeAgentStream",
                    "bedrock-agentcore:InvokeAgentRuntimeWithWebSocketStream"
                ],
                resources=["*"]
            )
        )

        # Add API Gateway invoke permissions
        self.authenticated_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["execute-api:Invoke"],
                resources=[api_gateway_arn]
            )
        )

        # Add AWS Location permissions
        self.authenticated_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "geo:GetMapStyleDescriptor",
                    "geo:GetMapSprites",
                    "geo:GetMapGlyphs",
                    "geo:GetMapTile",
                    "geo:SearchPlaceIndexForText",
                    "geo:SearchPlaceIndexForSuggestions",
                    "geo:GetPlace",
                ],
                resources=["*"]
            )
        )

        # Attach role to Identity Pool
        cognito.CfnIdentityPoolRoleAttachment(
            self, "IdentityPoolRoleAttachment",
            identity_pool_id=self.identity_pool.ref,
            roles={
                "authenticated": self.authenticated_role.role_arn
            }
        )

        # Create AppUsersGroup
        app_users_group = cognito.CfnUserPoolGroup(
            self, "AppUsersGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="AppUsersGroup",
            description="Group for application users"
        )

        # Create initial AppUser
        app_user = cognito.CfnUserPoolUser(
            self, "AppUser",
            user_pool_id=self.user_pool.user_pool_id,
            username="AppUser",
            user_attributes=[
                cognito.CfnUserPoolUser.AttributeTypeProperty(name="email", value=user_email.value_as_string),
                cognito.CfnUserPoolUser.AttributeTypeProperty(name="email_verified", value="true"),
                cognito.CfnUserPoolUser.AttributeTypeProperty(name="name", value=user_name.value_as_string),
                cognito.CfnUserPoolUser.AttributeTypeProperty(name="custom:customerId", value=customer_id),
            ],
            desired_delivery_mediums=["EMAIL"],
            force_alias_creation=False
        )

        user_to_group_attachment = cognito.CfnUserPoolUserToGroupAttachment(
            self, "AppUserToGroupAttachment",
            user_pool_id=self.user_pool.user_pool_id,
            group_name=app_users_group.group_name,
            username=app_user.username
        )

        user_to_group_attachment.add_dependency(app_users_group)
        user_to_group_attachment.add_dependency(app_user)

        # Outputs
        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id, export_name="QSR-UserPoolId")
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id, export_name="QSR-UserPoolClientId")
        CfnOutput(self, "IdentityPoolId", value=self.identity_pool.ref, export_name="QSR-IdentityPoolId")
        CfnOutput(self, "Region", value=self.region, export_name="QSR-Region")
        CfnOutput(self, "AuthenticatedRoleArn", value=self.authenticated_role.role_arn, export_name="QSR-AuthenticatedRoleArn")
        CfnOutput(self, "AppUserCustomerId", value=customer_id, export_name="QSR-AppUserCustomerId")
        CfnOutput(self, "AppUserName", value=user_name.value_as_string, export_name="QSR-AppUserName")
        CfnOutput(self, "AppUserEmail", value=user_email.value_as_string, export_name="QSR-AppUserEmail")
