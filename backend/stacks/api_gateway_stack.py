from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_logs as logs,
    aws_iam as iam,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class ApiGatewayStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cognito_stack, lambda_stack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Access Logs
        access_log_group = logs.LogGroup(
            self, "ApiAccessLogs",
            log_group_name="/aws/apigateway/qsr-api-access-logs",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create API
        self.api = apigateway.RestApi(
            self, "QSRApi",
            rest_api_name="QSR Ordering API",
            description="REST API for QSR ordering system with IAM authentication",
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                access_log_destination=apigateway.LogGroupLogDestination(access_log_group),
                access_log_format=apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True, http_method=True, ip=True, protocol=True,
                    request_time=True, resource_path=True, response_length=True,
                    status=True, user=True
                ),
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"]
            )
        )

        # Models
        success_model = self.api.add_model(
            "SuccessResponse",
            content_type="application/json",
            model_name="SuccessResponse",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Success Response",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "statusCode": apigateway.JsonSchema(type=apigateway.JsonSchemaType.INTEGER),
                    "body": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                }
            )
        )

        error_model = self.api.add_model(
            "ErrorResponse",
            content_type="application/json",
            model_name="ErrorResponse",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Error Response",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "statusCode": apigateway.JsonSchema(type=apigateway.JsonSchemaType.INTEGER),
                    "message": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                }
            )
        )

        add_to_cart_req = self.api.add_model(
            "AddToCartRequest",
            content_type="application/json",
            model_name="AddToCartRequest",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Add To Cart Request",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "customerId": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "locationId": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "items": apigateway.JsonSchema(
                        type=apigateway.JsonSchemaType.ARRAY,
                        items=apigateway.JsonSchema(
                            type=apigateway.JsonSchemaType.OBJECT,
                            properties={
                                "itemId": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                                "quantity": apigateway.JsonSchema(type=apigateway.JsonSchemaType.INTEGER)
                            },
                            required=["itemId", "quantity"]
                        )
                    )
                },
                required=["customerId", "locationId", "items"]
            )
        )

        place_order_req = self.api.add_model(
            "PlaceOrderRequest",
            content_type="application/json",
            model_name="PlaceOrderRequest",
            schema=apigateway.JsonSchema(
                schema=apigateway.JsonSchemaVersion.DRAFT4,
                title="Place Order Request",
                type=apigateway.JsonSchemaType.OBJECT,
                properties={
                    "customerId": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING),
                    "locationId": apigateway.JsonSchema(type=apigateway.JsonSchemaType.STRING)
                },
                required=["customerId", "locationId"]
            )
        )

        validator = apigateway.RequestValidator(
            self, "RequestValidator",
            rest_api=self.api,
            request_validator_name="request-body-validator",
            validate_request_body=True,
            validate_request_parameters=True
        )

        # Integrations
        def create_integration(func):
            return apigateway.LambdaIntegration(func, proxy=True, allow_test_invoke=True)

        integrations = {
            'profile': create_integration(lambda_stack.get_customer_profile),
            'orders': create_integration(lambda_stack.get_previous_orders),
            'menu': create_integration(lambda_stack.get_menu),
            'add_to_cart': create_integration(lambda_stack.add_to_cart),
            'get_cart': create_integration(lambda_stack.get_cart),
            'update_cart': create_integration(lambda_stack.update_cart),
            'place_order': create_integration(lambda_stack.place_order),
            'nearest': create_integration(lambda_stack.get_nearest_locations),
            'route': create_integration(lambda_stack.find_location_along_route),
            'geocode': create_integration(lambda_stack.geocode_address),
        }

        # Routes
        responses = [
            apigateway.MethodResponse(status_code='200', response_models={'application/json': success_model}, response_parameters={'method.response.header.Access-Control-Allow-Origin': True}),
            apigateway.MethodResponse(status_code='400', response_models={'application/json': error_model}),
            apigateway.MethodResponse(status_code='401', response_models={'application/json': error_model}),
            apigateway.MethodResponse(status_code='500', response_models={'application/json': error_model}),
        ]

        customers = self.api.root.add_resource('customers')
        
        prof = customers.add_resource('profile')
        prof.add_method('GET', integrations['profile'], authorization_type=apigateway.AuthorizationType.IAM,
                        operation_name='GetCustomerProfile', method_responses=responses,
                        request_parameters={'method.request.querystring.customerId': True})

        ords = customers.add_resource('orders')
        ords.add_method('GET', integrations['orders'], authorization_type=apigateway.AuthorizationType.IAM,
                        operation_name='GetPreviousOrders', method_responses=responses,
                        request_parameters={'method.request.querystring.customerId': True})

        menu = self.api.root.add_resource('menu')
        menu.add_method('GET', integrations['menu'], authorization_type=apigateway.AuthorizationType.IAM,
                        operation_name='GetMenu', method_responses=responses,
                        request_parameters={'method.request.querystring.locationId': True})

        cart = self.api.root.add_resource('cart')
        cart.add_method('POST', integrations['add_to_cart'], authorization_type=apigateway.AuthorizationType.IAM,
                        operation_name='AddToCart', request_validator=validator,
                        request_models={'application/json': add_to_cart_req}, method_responses=responses)
        cart.add_method('GET', integrations['get_cart'], authorization_type=apigateway.AuthorizationType.IAM,
                        operation_name='GetCart', method_responses=responses,
                        request_parameters={'method.request.querystring.customerId': True})
        cart.add_method('PUT', integrations['update_cart'], authorization_type=apigateway.AuthorizationType.IAM,
                        operation_name='UpdateCart', method_responses=responses)

        order = self.api.root.add_resource('order')
        order.add_method('POST', integrations['place_order'], authorization_type=apigateway.AuthorizationType.IAM,
                         operation_name='PlaceOrder', request_validator=validator,
                         request_models={'application/json': place_order_req}, method_responses=responses)

        locations = self.api.root.add_resource('locations')
        nearest = locations.add_resource('nearest')
        nearest.add_method('GET', integrations['nearest'], authorization_type=apigateway.AuthorizationType.IAM,
                           operation_name='GetNearestLocations', method_responses=responses,
                           request_parameters={'method.request.querystring.latitude': True, 'method.request.querystring.longitude': True})

        route = locations.add_resource('route')
        route.add_method('GET', integrations['route'], authorization_type=apigateway.AuthorizationType.IAM,
                         operation_name='FindLocationAlongRoute', method_responses=responses,
                         request_parameters={'method.request.querystring.startLatitude': True, 'method.request.querystring.startLongitude': True, 'method.request.querystring.endLatitude': True, 'method.request.querystring.endLongitude': True})

        geocode = locations.add_resource('geocode')
        geocode.add_method('GET', integrations['geocode'], authorization_type=apigateway.AuthorizationType.IAM,
                           operation_name='GeocodeAddress', method_responses=responses,
                           request_parameters={'method.request.querystring.address': True})

        CfnOutput(self, "ApiGatewayUrl", value=self.api.url, export_name="QSR-ApiGatewayUrl")
        CfnOutput(self, "ApiGatewayId", value=self.api.rest_api_id, export_name="QSR-ApiGatewayId")
        CfnOutput(self, "ApiGatewayArn", value=f"arn:aws:execute-api:{self.region}:{self.account}:{self.api.rest_api_id}/*", export_name="QSR-ApiGatewayArn")

        # ==============================================================================
        # API Gateway Account CloudWatch Role (AUTOMATIC LOGS)
        # ==============================================================================
        cw_logs_role = iam.Role(
            self,
            "ApiGatewayCWRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                )
            ],
        )

        apigateway.CfnAccount(
            self,
            "ApiGatewayAccountConfig",
            cloud_watch_role_arn=cw_logs_role.role_arn
        )
