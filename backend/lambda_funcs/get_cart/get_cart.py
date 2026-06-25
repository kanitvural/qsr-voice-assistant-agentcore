import os
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
CARTS_TABLE_NAME = os.environ.get('CARTS_TABLE_NAME')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] GetCart event: {json.dumps(event)}")
    
    try:
        if event.get('queryStringParameters'):
            params = event['queryStringParameters']
        else:
            params = json.loads(event.get('body', '{}'))
            
        customer_id = params.get('customerId')
        
        if not customer_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'customerId parameter is required'})
            }
            
        table = dynamodb.Table(CARTS_TABLE_NAME)
        response = table.get_item(Key={'PK': f'CUSTOMER#{customer_id}'})
        cart = response.get('Item')
        
        if not cart or not cart.get('items') or len(cart['items']) == 0:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'cart': None,
                    'items': [],
                    'itemCount': 0,
                    'message': 'Cart is empty'
                }, default=decimal_default)
            }
            
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart['items'])
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'cart': {
                    'customerId': cart.get('customerId'),
                    'locationId': cart.get('locationId'),
                    'items': cart.get('items'),
                    'itemCount': len(cart.get('items')),
                    'subtotal': float(subtotal),
                    'createdAt': cart.get('createdAt'),
                    'updatedAt': cart.get('updatedAt')
                }
            }, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error getting cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to get cart',
                'message': str(e)
            })
        }
