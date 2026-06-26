from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct
import os

class LambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, dynamodb_stack, location_stack, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Base path for lambda functions
        lambda_base_path = os.path.join(os.path.dirname(__file__), '..', 'lambda_funcs')

        # 1. GetCustomerProfile
        self.get_customer_profile = _lambda.Function(
            self, "GetCustomerProfile",
            function_name="QSR-GetCustomerProfile",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="get_customer_profile.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'get_customer_profile')),
            environment={
                "CUSTOMERS_TABLE_NAME": dynamodb_stack.customers_table.table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Retrieve customer profile including name, email, phone, loyalty points, and tier."
        )
        dynamodb_stack.customers_table.grant_read_data(self.get_customer_profile)

        # 2. GetPreviousOrders
        self.get_previous_orders = _lambda.Function(
            self, "GetPreviousOrders",
            function_name="QSR-GetPreviousOrders",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="get_previous_orders.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'get_previous_orders')),
            environment={
                "ORDERS_TABLE_NAME": dynamodb_stack.orders_table.table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Retrieve customer order history (last 5 orders)."
        )
        dynamodb_stack.orders_table.grant_read_data(self.get_previous_orders)

        # 3. GetMenu
        self.get_menu = _lambda.Function(
            self, "GetMenu",
            function_name="QSR-GetMenu",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="get_menu.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'get_menu')),
            environment={
                "MENU_TABLE_NAME": dynamodb_stack.menu_table.table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Retrieve location-specific menu items."
        )
        dynamodb_stack.menu_table.grant_read_data(self.get_menu)

        # 4. AddToCart
        self.add_to_cart = _lambda.Function(
            self, "AddToCart",
            function_name="QSR-AddToCart",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="add_to_cart.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'add_to_cart')),
            environment={
                "MENU_TABLE_NAME": dynamodb_stack.menu_table.table_name,
                "CARTS_TABLE_NAME": dynamodb_stack.carts_table.table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Add menu items to shopping cart with availability verification."
        )
        dynamodb_stack.menu_table.grant_read_data(self.add_to_cart)
        dynamodb_stack.carts_table.grant_read_write_data(self.add_to_cart)

        # 5. GetCart
        self.get_cart = _lambda.Function(
            self, "GetCart",
            function_name="QSR-GetCart",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="get_cart.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'get_cart')),
            environment={
                "CARTS_TABLE_NAME": dynamodb_stack.carts_table.table_name,
            },
            timeout=Duration.seconds(10),
            memory_size=256,
            description="Get current cart contents for a customer."
        )
        dynamodb_stack.carts_table.grant_read_data(self.get_cart)

        # 6. UpdateCart
        self.update_cart = _lambda.Function(
            self, "UpdateCart",
            function_name="QSR-UpdateCart",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="update_cart.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'update_cart')),
            environment={
                "CARTS_TABLE_NAME": dynamodb_stack.carts_table.table_name,
            },
            timeout=Duration.seconds(10),
            memory_size=256,
            description="Update cart: clear all items, remove a specific item, update item quantity, or change pickup location."
        )
        dynamodb_stack.carts_table.grant_read_write_data(self.update_cart)

        # 7. PlaceOrder
        self.place_order = _lambda.Function(
            self, "PlaceOrder",
            function_name="QSR-PlaceOrder",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="place_order.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'place_order')),
            environment={
                "CARTS_TABLE_NAME": dynamodb_stack.carts_table.table_name,
                "ORDERS_TABLE_NAME": dynamodb_stack.orders_table.table_name,
                "LOCATIONS_TABLE_NAME": dynamodb_stack.locations_table.table_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Create order from cart with automatic tax calculation based on location."
        )
        dynamodb_stack.carts_table.grant_read_write_data(self.place_order)
        dynamodb_stack.orders_table.grant_read_write_data(self.place_order)
        dynamodb_stack.locations_table.grant_read_data(self.place_order)

        # 8. GetNearestLocations
        self.get_nearest_locations = _lambda.Function(
            self, "GetNearestLocations",
            function_name="QSR-GetNearestLocations",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="get_nearest_locations.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'get_nearest_locations')),
            environment={
                "LOCATIONS_TABLE_NAME": dynamodb_stack.locations_table.table_name,
                "PLACE_INDEX_NAME": location_stack.place_index.index_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Find nearest restaurant locations using GPS coordinates."
        )
        dynamodb_stack.locations_table.grant_read_data(self.get_nearest_locations)
        self.get_nearest_locations.add_to_role_policy(iam.PolicyStatement(
            actions=["geo:SearchPlaceIndexForPosition"],
            resources=[location_stack.place_index.attr_index_arn]
        ))

        # 9. FindLocationAlongRoute
        self.find_location_along_route = _lambda.Function(
            self, "FindLocationAlongRoute",
            function_name="QSR-FindLocationAlongRoute",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="find_location_along_route.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'find_location_along_route')),
            environment={
                "LOCATIONS_TABLE_NAME": dynamodb_stack.locations_table.table_name,
                "ROUTE_CALCULATOR_NAME": location_stack.route_calculator.calculator_name,
            },
            timeout=Duration.seconds(60),
            memory_size=512,
            description="Find restaurant locations along a driving route with detour time calculation."
        )
        dynamodb_stack.locations_table.grant_read_data(self.find_location_along_route)
        self.find_location_along_route.add_to_role_policy(iam.PolicyStatement(
            actions=["geo:CalculateRoute"],
            resources=[location_stack.route_calculator.attr_calculator_arn]
        ))

        # 10. GeocodeAddress
        self.geocode_address = _lambda.Function(
            self, "GeocodeAddress",
            function_name="QSR-GeocodeAddress",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="geocode_address.handler",
            code=_lambda.Code.from_asset(os.path.join(lambda_base_path, 'geocode_address')),
            environment={
                "PLACE_INDEX_NAME": location_stack.place_index.index_name,
            },
            timeout=Duration.seconds(30),
            memory_size=256,
            description="Convert street address to GPS coordinates using AWS Location Services."
        )
        self.geocode_address.add_to_role_policy(iam.PolicyStatement(
            actions=["geo:SearchPlaceIndexForText"],
            resources=[location_stack.place_index.attr_index_arn]
        ))

        # Stack Outputs
        CfnOutput(self, "GetCustomerProfileFunctionArn", value=self.get_customer_profile.function_arn, export_name="GetCustomerProfileFunctionArn")
        CfnOutput(self, "GetPreviousOrdersFunctionArn", value=self.get_previous_orders.function_arn, export_name="GetPreviousOrdersFunctionArn")
        CfnOutput(self, "GetMenuFunctionArn", value=self.get_menu.function_arn, export_name="GetMenuFunctionArn")
        CfnOutput(self, "AddToCartFunctionArn", value=self.add_to_cart.function_arn, export_name="AddToCartFunctionArn")
        CfnOutput(self, "GetCartFunctionArn", value=self.get_cart.function_arn)
        CfnOutput(self, "UpdateCartFunctionArn", value=self.update_cart.function_arn)
        CfnOutput(self, "PlaceOrderFunctionArn", value=self.place_order.function_arn, export_name="PlaceOrderFunctionArn")
        CfnOutput(self, "GetNearestLocationsFunctionArn", value=self.get_nearest_locations.function_arn, export_name="GetNearestLocationsFunctionArn")
        CfnOutput(self, "FindLocationAlongRouteFunctionArn", value=self.find_location_along_route.function_arn, export_name="FindLocationAlongRouteFunctionArn")
        CfnOutput(self, "GeocodeAddressFunctionArn", value=self.geocode_address.function_arn, export_name="GeocodeAddressFunctionArn")
