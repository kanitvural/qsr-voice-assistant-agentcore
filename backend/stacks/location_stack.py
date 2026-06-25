from aws_cdk import (
    Stack,
    aws_location as location,
    CfnOutput,
    CfnTag
)
from constructs import Construct

class LocationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        tags = [
            CfnTag(key="Environment", value="Development"),
            CfnTag(key="ManagedBy", value="CDK"),
            CfnTag(key="Project", value="QSR-Ordering"),
        ]

        # Create Place Index for geocoding and place search
        self.place_index = location.CfnPlaceIndex(
            self, "QSRPlaceIndex",
            index_name="QSRRestaurantIndex",
            data_source="Esri",
            description="Place index for QSR restaurant geocoding and search",
            pricing_plan="RequestBasedUsage"
            # Note: CfnPlaceIndex does not natively accept tags via props in some CDK versions, 
            # so tags can be applied via cdk.Tags.of(self.place_index) if needed.
        )

        # Create Route Calculator for route optimization
        self.route_calculator = location.CfnRouteCalculator(
            self, "QSRRouteCalculator",
            calculator_name="QSRRouteCalculator",
            data_source="Esri",
            description="Route calculator for QSR restaurant route optimization",
            pricing_plan="RequestBasedUsage"
        )

        # Create Map for interactive visualization
        self.map = location.CfnMap(
            self, "QSRMap",
            map_name="QSRRestaurantMap",
            configuration=location.CfnMap.MapConfigurationProperty(
                style="VectorEsriNavigation"
            ),
            description="Map for QSR restaurant location visualization and coordinate selection",
            pricing_plan="RequestBasedUsage"
        )

        # Stack Outputs
        CfnOutput(self, "PlaceIndexName", value=self.place_index.index_name, export_name="QSR-PlaceIndexName")
        CfnOutput(self, "PlaceIndexArn", value=self.place_index.attr_index_arn, export_name="QSR-PlaceIndexArn")
        CfnOutput(self, "RouteCalculatorName", value=self.route_calculator.calculator_name, export_name="QSR-RouteCalculatorName")
        CfnOutput(self, "RouteCalculatorArn", value=self.route_calculator.attr_calculator_arn, export_name="QSR-RouteCalculatorArn")
        CfnOutput(self, "MapName", value=self.map.map_name, export_name="QSR-MapName")
        CfnOutput(self, "MapArn", value=self.map.attr_map_arn, export_name="QSR-MapArn")
