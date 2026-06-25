import os
import json
import boto3
import re
from decimal import Decimal

location_client = boto3.client('location')
PLACE_INDEX_NAME = os.environ.get('PLACE_INDEX_NAME')

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

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] GeocodeAddress event: {json.dumps(event)}")
    
    try:
        if event.get('queryStringParameters'):
            params = event['queryStringParameters']
        else:
            params = json.loads(event.get('body', '{}'))
            
        address = params.get('address')
        
        if not address:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Address parameter is required'})
            }
            
        result = location_client.search_place_index_for_text(
            IndexName=PLACE_INDEX_NAME,
            Text=address,
            MaxResults=1
        )
        
        if not result.get('Results'):
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'coordinates': None,
                    'message': 'No results found for the provided address'
                })
            }
            
        place = result['Results'][0]['Place']
        coordinates = {
            'latitude': place['Geometry']['Point'][1],
            'longitude': place['Geometry']['Point'][0],
            'label': expand_address(place.get('Label')),
            'address': expand_address(place.get('Label'))
        }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'coordinates': coordinates}, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error geocoding address: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to geocode address',
                'message': str(e)
            })
        }
