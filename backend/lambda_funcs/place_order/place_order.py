import os
import json
import time
import random
import string
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')

CARTS_TABLE_NAME = os.environ.get('CARTS_TABLE_NAME')
ORDERS_TABLE_NAME = os.environ.get('ORDERS_TABLE_NAME')
LOCATIONS_TABLE_NAME = os.environ.get('LOCATIONS_TABLE_NAME')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def generate_order_id():
    chars = string.ascii_lowercase + string.digits
    rand_str = ''.join(random.choice(chars) for _ in range(9))
    return f"order-{int(time.time()*1000)}-{rand_str}"

def handler(event, context):
    print(f"[DEBUG] PlaceOrder event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        customer_id = body.get('customerId')
        location_id = body.get('locationId')
        
        if not customer_id or not location_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required parameters: customerId, locationId'})
            }
            
        carts_table = dynamodb.Table(CARTS_TABLE_NAME)
        cart_response = carts_table.get_item(Key={'PK': f'CUSTOMER#{customer_id}'})
        cart = cart_response.get('Item')
        
        if not cart or not cart.get('items') or len(cart['items']) == 0:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'Cart is empty',
                    'message': 'No items in cart. Please add items before placing an order.'
                })
            }
            
        locations_table = dynamodb.Table(LOCATIONS_TABLE_NAME)
        loc_response = locations_table.get_item(Key={'PK': f'LOCATION#{location_id}'})
        location = loc_response.get('Item')
        
        if not location:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'Location not found',
                    'message': f'Location {location_id} not found. Please populate the Locations table with data.'
                })
            }
            
        tax_rate = float(location.get('taxRate', 0))
        
        subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in cart['items'])
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        order_id = generate_order_id()
        timestamp = int(time.time() * 1000)
        
        order = {
            'PK': f'CUSTOMER#{customer_id}',
            'SK': f'ORDER#{order_id}#{timestamp}',
            'GSI1PK': f'LOCATION#{location_id}',
            'GSI1SK': f'ORDER#{timestamp}',
            'customerId': customer_id,
            'orderId': order_id,
            'locationId': location_id,
            'items': cart['items'],
            'subtotal': subtotal,
            'tax': tax,
            'total': total,
            'status': 'confirmed',
            'timestamp': timestamp,
            'createdAt': datetime.utcnow().isoformat() + 'Z'
        }
        
        orders_table = dynamodb.Table(ORDERS_TABLE_NAME)
        
        # DynamoDB Decimal conversion hack for float
        # Boto3 doesn't automatically convert float to Decimal in put_item, so we should convert manually.
        order['subtotal'] = Decimal(str(round(subtotal, 2)))
        order['tax'] = Decimal(str(round(tax, 2)))
        order['total'] = Decimal(str(round(total, 2)))
        
        for item in order['items']:
            item['price'] = Decimal(str(item['price']))
        
        orders_table.put_item(Item=order)
        
        carts_table.delete_item(Key={'PK': f'CUSTOMER#{customer_id}'})
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'order': order,
                'message': 'Order placed successfully'
            }, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error placing order: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to place order',
                'message': str(e)
            })
        }
