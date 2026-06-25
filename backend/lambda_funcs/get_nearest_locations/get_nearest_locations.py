import os
import json
import boto3
import math
import re
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
LOCATIONS_TABLE = os.environ.get('LOCATIONS_TABLE_NAME')

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

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def handler(event, context):
    print(f"[DEBUG] GetNearestLocations event: {json.dumps(event)}")
    
    try:
        if event.get('queryStringParameters'):
            params = event['queryStringParameters']
        else:
            params = json.loads(event.get('body', '{}'))
            
        latitude = params.get('latitude')
        longitude = params.get('longitude')
        max_results = int(params.get('maxResults', 5))
        
        if latitude is None or longitude is None:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid latitude or longitude'})
            }
            
        latitude = float(latitude)
        longitude = float(longitude)
        
        table = dynamodb.Table(LOCATIONS_TABLE)
        response = table.scan()
        locations = response.get('Items', [])
        
        if not locations:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'locations': [],
                    'message': 'No locations found. Please populate the Locations table with data.'
                })
            }
            
        for loc in locations:
            loc['distance'] = calculate_distance(
                latitude,
                longitude,
                float(loc['latitude']),
                float(loc['longitude'])
            )
            
        locations.sort(key=lambda x: x['distance'])
        nearest_locations = locations[:max_results]
        
        nearest_locations = [expand_address_fields(loc) for loc in nearest_locations]
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'locations': nearest_locations}, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error getting nearest locations: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to get nearest locations',
                'message': str(e)
            })
        }
