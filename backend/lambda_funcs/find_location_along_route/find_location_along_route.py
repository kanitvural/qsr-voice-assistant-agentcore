import os
import json
import boto3
import re
from decimal import Decimal

# Initialize clients
dynamodb = boto3.resource('dynamodb')
location_client = boto3.client('location')

LOCATIONS_TABLE = os.environ.get('LOCATIONS_TABLE_NAME')
ROUTE_CALCULATOR_NAME = os.environ.get('ROUTE_CALCULATOR_NAME')

ADDR_ABBR = {
    'Dr': 'Drive', 'St': 'Street', 'Ln': 'Lane', 'Pkwy': 'Parkway',
    'Blvd': 'Boulevard', 'Ave': 'Avenue', 'Ct': 'Court', 'Rd': 'Road',
    'Hwy': 'Highway', 'Cir': 'Circle', 'Pl': 'Place', 'Ter': 'Terrace',
    'Trl': 'Trail', 'Fwy': 'Freeway', 'Expy': 'Expressway'
}

def expand_address(s):
    if not s:
        return s
    r = s
    for abbr, full in ADDR_ABBR.items():
        r = re.sub(r'\b' + abbr + r'\b\.?', full, r)
    return r

def expand_address_fields(obj):
    if not obj:
        return obj
    for field in ['address', 'street', 'label', 'homeAddress', 'locationName']:
        if field in obj and obj[field]:
            obj[field] = expand_address(obj[field])
    return obj

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] FindLocationAlongRoute event: {json.dumps(event)}")
    
    try:
        # Determine if params are in query string or body
        if event.get('queryStringParameters'):
            params = event['queryStringParameters']
        else:
            params = json.loads(event.get('body', '{}'))
            
        start_lat = float(params.get('startLatitude'))
        start_lon = float(params.get('startLongitude'))
        end_lat = float(params.get('endLatitude'))
        end_lon = float(params.get('endLongitude'))
        max_detour_minutes = int(params.get('maxDetourMinutes', 10))
        
        # Calculate main route
        main_route = location_client.calculate_route(
            CalculatorName=ROUTE_CALCULATOR_NAME,
            DeparturePosition=[start_lon, start_lat],
            DestinationPosition=[end_lon, end_lat]
        )
        
        main_route_duration = main_route['Summary']['DurationSeconds'] / 60.0
        
        # Scan all locations
        table = dynamodb.Table(LOCATIONS_TABLE)
        # Note: Scanning is used in the original code because it's a demo.
        response = table.scan()
        locations = response.get('Items', [])
        
        if not locations:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'locations': [],
                    'message': 'No locations found. Please populate the Locations table with data.'
                }, default=decimal_default)
            }
            
        valid_locations = []
        
        # Calculate detour for each location
        for loc in locations:
            loc_lat = float(loc['latitude'])
            loc_lon = float(loc['longitude'])
            
            try:
                # Route from start to location
                route_to = location_client.calculate_route(
                    CalculatorName=ROUTE_CALCULATOR_NAME,
                    DeparturePosition=[start_lon, start_lat],
                    DestinationPosition=[loc_lon, loc_lat]
                )
                
                # Route from location to end
                route_from = location_client.calculate_route(
                    CalculatorName=ROUTE_CALCULATOR_NAME,
                    DeparturePosition=[loc_lon, loc_lat],
                    DestinationPosition=[end_lon, end_lat]
                )
                
                total_duration = (route_to['Summary']['DurationSeconds'] + route_from['Summary']['DurationSeconds']) / 60.0
                detour_minutes = total_duration - main_route_duration
                
                if detour_minutes <= max_detour_minutes:
                    loc['detourMinutes'] = detour_minutes
                    valid_locations.append(loc)
            except Exception as e:
                print(f"[ERROR] Error calculating route for location {loc.get('locationId')}: {str(e)}")
                
        # Sort by detour time
        valid_locations.sort(key=lambda x: x['detourMinutes'])
        
        # Expand address fields
        valid_locations = [expand_address_fields(loc) for loc in valid_locations]
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'locations': valid_locations,
                'mainRouteDurationMinutes': main_route_duration
            }, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error finding location along route: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to find location along route',
                'message': str(e)
            })
        }
