from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct


class DynamoDBStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Customers Table
        # PK: CUSTOMER#{customerId}, SK: PROFILE
        self.customers_table = dynamodb.Table(
            self, "CustomersTable",
            table_name="QSR-Customers",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development
            point_in_time_recovery=True
        )

        # Orders Table
        # PK: CUSTOMER#{customerId}, SK: ORDER#{orderId}#{timestamp}
        # GSI1: PK: LOCATION#{locationId}, SK: ORDER#{timestamp}
        self.orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="QSR-Orders",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development
            point_in_time_recovery=True
        )

        # Add GSI for location-based queries
        self.orders_table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(name="GSI1PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="GSI1SK", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Menu Table
        # PK: LOCATION#{locationId}#ITEM#{itemId}
        self.menu_table = dynamodb.Table(
            self, "MenuTable",
            table_name="QSR-Menu",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development
            point_in_time_recovery=True
        )

        # Carts Table
        # PK: SESSION#{sessionId}
        # TTL: expiresAt (24 hours from creation)
        self.carts_table = dynamodb.Table(
            self, "CartsTable",
            table_name="QSR-Carts",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development
            time_to_live_attribute="expiresAt",
            point_in_time_recovery=True
        )

        # Locations Table
        # PK: LOCATION#{locationId}
        self.locations_table = dynamodb.Table(
            self, "LocationsTable",
            table_name="QSR-Locations",
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # For development
            point_in_time_recovery=True
        )

        # Stack Outputs
        CfnOutput(self, "CustomersTableName", value=self.customers_table.table_name, export_name="QSR-CustomersTableName")
        CfnOutput(self, "CustomersTableArn", value=self.customers_table.table_arn, export_name="QSR-CustomersTableArn")
        CfnOutput(self, "OrdersTableName", value=self.orders_table.table_name, export_name="QSR-OrdersTableName")
        CfnOutput(self, "OrdersTableArn", value=self.orders_table.table_arn, export_name="QSR-OrdersTableArn")
        CfnOutput(self, "MenuTableName", value=self.menu_table.table_name, export_name="QSR-MenuTableName")
        CfnOutput(self, "MenuTableArn", value=self.menu_table.table_arn, export_name="QSR-MenuTableArn")
        CfnOutput(self, "CartsTableName", value=self.carts_table.table_name, export_name="QSR-CartsTableName")
        CfnOutput(self, "CartsTableArn", value=self.carts_table.table_arn, export_name="QSR-CartsTableArn")
        CfnOutput(self, "LocationsTableName", value=self.locations_table.table_name, export_name="QSR-LocationsTableName")
        CfnOutput(self, "LocationsTableArn", value=self.locations_table.table_arn, export_name="QSR-LocationsTableArn")
