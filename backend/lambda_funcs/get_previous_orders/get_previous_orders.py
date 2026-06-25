import os
import json
import boto3
import re
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
ORDERS_TABLE_NAME = os.environ.get('ORDERS_TABLE_NAME')

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
        if field in obj and obj.get(field):
            obj[field] = expand_address(obj[field])
    return obj

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] GetPreviousOrders event: {json.dumps(event)}")
    
    try:
        if event.get('queryStringParameters'):
            params = event['queryStringParameters']
        else:
            params = json.loads(event.get('body', '{}'))
            
        customer_id = params.get('customerId')
        limit = int(params.get('limit', 5))
        
        if not customer_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'customerId parameter is required'})
            }
            
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        response = table.query(
            KeyConditionExpression=Key('PK').eq(f'CUSTOMER#{customer_id}') & Key('SK').begins_with('ORDER#'),
            ScanIndexForward=False, # descending
            Limit=limit
        )
        
        orders = response.get('Items', [])
        
        if not orders:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'orders': [],
                    'message': f'No orders found for customer {customer_id}. Please populate the Orders table with data.'
                }, default=decimal_default)
            }
            
        orders = [expand_address_fields(o) for o in orders]
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'orders': orders}, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error getting previous orders: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to get previous orders',
                'message': str(e)
            })
        }
