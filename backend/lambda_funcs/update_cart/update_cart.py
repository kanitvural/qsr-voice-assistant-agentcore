import os
import json
import time
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
CARTS_TABLE_NAME = os.environ.get('CARTS_TABLE_NAME')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def respond(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps(body, default=decimal_default)
    }

def handler(event, context):
    print(f"[DEBUG] UpdateCart event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        customer_id = body.get('customerId')
        action = body.get('action')
        
        if not customer_id or not action:
            return respond(400, {
                'error': 'Missing required parameters: customerId and action',
                'validActions': ['clear', 'remove_item', 'update_quantity', 'change_location']
            })
            
        cart_key = {'PK': f'CUSTOMER#{customer_id}'}
        now = int(time.time())
        ttl = now + (24 * 60 * 60)
        
        carts_table = dynamodb.Table(CARTS_TABLE_NAME)
        
        # Action: clear
        if action == 'clear':
            carts_table.delete_item(Key=cart_key)
            return respond(200, {'message': 'Cart cleared', 'items': [], 'itemCount': 0})
            
        # Get cart
        cart_result = carts_table.get_item(Key=cart_key)
        cart = cart_result.get('Item')
        
        if not cart or not cart.get('items') or len(cart['items']) == 0:
            return respond(400, {'error': 'Cart is empty', 'items': [], 'itemCount': 0})
            
        items = list(cart['items'])
        location_id = cart.get('locationId')
        
        # Action: remove_item
        if action == 'remove_item':
            item_id = body.get('itemId')
            if not item_id:
                return respond(400, {'error': 'itemId is required for remove_item action'})
                
            before_len = len(items)
            items = [i for i in items if i['itemId'] != item_id]
            
            if len(items) == before_len:
                return respond(404, {'error': f'Item {item_id} not found in cart'})
                
            if len(items) == 0:
                carts_table.delete_item(Key=cart_key)
                return respond(200, {'message': 'Item removed. Cart is now empty.', 'items': [], 'itemCount': 0})
                
        # Action: update_quantity
        elif action == 'update_quantity':
            item_id = body.get('itemId')
            quantity = body.get('quantity')
            
            if not item_id or quantity is None:
                return respond(400, {'error': 'itemId and quantity are required for update_quantity action'})
                
            idx = next((i for i, item in enumerate(items) if item['itemId'] == item_id), -1)
            
            if idx == -1:
                return respond(404, {'error': f'Item {item_id} not found in cart'})
                
            quantity = int(quantity)
            if quantity <= 0:
                items.pop(idx)
                if len(items) == 0:
                    carts_table.delete_item(Key=cart_key)
                    return respond(200, {'message': 'Item removed. Cart is now empty.', 'items': [], 'itemCount': 0})
            else:
                items[idx]['quantity'] = quantity
                
        # Action: change_location
        elif action == 'change_location':
            new_location_id = body.get('newLocationId')
            if not new_location_id:
                return respond(400, {'error': 'newLocationId is required for change_location action'})
            location_id = new_location_id
            
        # Update cart
        updated_cart = carts_table.update_item(
            Key=cart_key,
            UpdateExpression='SET #items = :items, locationId = :locationId, updatedAt = :updatedAt, expiresAt = :expiresAt',
            ExpressionAttributeNames={'#items': 'items'},
            ExpressionAttributeValues={
                ':items': items,
                ':locationId': location_id,
                ':updatedAt': now,
                ':expiresAt': ttl
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_attrs = updated_cart.get('Attributes', {})
        subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items)
        
        return respond(200, {
            'cart': {
                'customerId': updated_attrs.get('customerId'),
                'locationId': updated_attrs.get('locationId'),
                'items': items,
                'itemCount': len(items),
                'subtotal': subtotal
            },
            'message': f'Cart updated ({action})'
        })
        
    except Exception as e:
        print(f"[ERROR] Error updating cart: {str(e)}")
        return respond(500, {'error': 'Failed to update cart', 'message': str(e)})
