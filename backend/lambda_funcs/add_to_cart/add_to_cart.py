import os
import json
import time
import boto3
from decimal import Decimal

# Initialize DynamoDB resource and clients
dynamodb = boto3.resource('dynamodb')
client = boto3.client('dynamodb')

MENU_TABLE_NAME = os.environ.get('MENU_TABLE_NAME')
CARTS_TABLE_NAME = os.environ.get('CARTS_TABLE_NAME')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] AddToCart event: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        customer_id = body.get('customerId')
        location_id = body.get('locationId')
        items = body.get('items')
        
        print(f"[DEBUG] Parsed request - customerId: {customer_id}, locationId: {location_id}, items count: {len(items) if items else 0}")
        
        if not customer_id or not location_id or not items or not isinstance(items, list) or len(items) == 0:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Missing required parameters: customerId, locationId, and items array (must contain at least one item)'})
            }
            
        for i, item in enumerate(items):
            if not item.get('itemId') or not item.get('quantity'):
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'Item at index {i} is missing required fields: itemId and quantity'})
                }
                
        # Batch get menu items
        keys_to_get = [{'PK': f'LOCATION#{location_id}#ITEM#{item["itemId"]}'} for item in items]
        
        # Boto3 batch_get_item format
        response = dynamodb.meta.client.batch_get_item(
            RequestItems={
                MENU_TABLE_NAME: {
                    'Keys': keys_to_get
                }
            }
        )
        
        fetched_items = response.get('Responses', {}).get(MENU_TABLE_NAME, [])
        # Convert DynamoDB dicts to regular dicts using boto3 TypeDeserializer
        # Boto3 resource handles deserialization automatically when using Table resource, but batch_get_item requires some care.
        # Actually, using resource batch_get_item is easier if we use Table objects, but we can't batch across tables easily. 
        # With meta.client, we get back native types if we use dynamodb resource, wait, meta.client.batch_get_item returns native types like Decimal!
        
        menu_items_map = {item['itemId']: item for item in fetched_items}
        
        items_added = []
        items_failed = []
        
        for req_item in items:
            item_id = req_item['itemId']
            menu_item = menu_items_map.get(item_id)
            
            if not menu_item:
                items_failed.append({
                    'itemId': item_id,
                    'quantity': req_item['quantity'],
                    'name': 'Unknown',
                    'error': 'Item no longer exists in this location'
                })
                continue
                
            if not menu_item.get('isAvailable', False):
                items_failed.append({
                    'itemId': item_id,
                    'quantity': req_item['quantity'],
                    'name': menu_item.get('name', 'Unknown'),
                    'error': 'Item not available'
                })
                continue
                
            items_added.append({
                'itemId': item_id,
                'name': menu_item['name'],
                'price': menu_item['price'],
                'quantity': req_item['quantity']
            })
            
        if not items_added:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'error': 'No valid items to add to cart',
                    'itemsFailed': items_failed,
                    'message': f'0 item(s) added, {len(items_failed)} item(s) failed'
                }, default=decimal_default)
            }
            
        carts_table = dynamodb.Table(CARTS_TABLE_NAME)
        
        # Get cart
        cart_response = carts_table.get_item(Key={'PK': f'CUSTOMER#{customer_id}'})
        cart = cart_response.get('Item')
        
        now = int(time.time())
        ttl = now + (24 * 60 * 60)
        
        if not cart:
            new_cart = {
                'PK': f'CUSTOMER#{customer_id}',
                'customerId': customer_id,
                'locationId': location_id,
                'items': items_added,
                'createdAt': now,
                'updatedAt': now,
                'expiresAt': ttl
            }
            # Put item handles Decimal conversion properly if we ensure types are right
            # But items_added has standard python floats from our mapping (if they were float originally)
            # Actually, Decimal floats are fine.
            carts_table.put_item(Item=new_cart)
            
            subtotal = sum(item['price'] * item['quantity'] for item in items_added)
            new_cart['itemCount'] = len(items_added)
            new_cart['subtotal'] = float(subtotal)
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'cart': new_cart,
                    'itemsAdded': items_added,
                    'itemsFailed': items_failed,
                    'message': f'Added {len(items_added)} item(s)' + (f', {len(items_failed)} item(s) failed' if items_failed else '')
                }, default=decimal_default)
            }
            
        # Update existing cart
        existing_items = cart.get('items', [])
        updated_items = list(existing_items)
        
        for new_item in items_added:
            found = False
            for exist_item in updated_items:
                if exist_item['itemId'] == new_item['itemId']:
                    exist_item['quantity'] += new_item['quantity']
                    found = True
                    break
            if not found:
                updated_items.append(new_item)
                
        updated_cart_response = carts_table.update_item(
            Key={'PK': f'CUSTOMER#{customer_id}'},
            UpdateExpression='SET #items = :items, updatedAt = :updatedAt, expiresAt = :expiresAt',
            ExpressionAttributeNames={'#items': 'items'},
            ExpressionAttributeValues={
                ':items': updated_items,
                ':updatedAt': now,
                ':expiresAt': ttl
            },
            ReturnValues='ALL_NEW'
        )
        
        updated_cart = updated_cart_response.get('Attributes', {})
        subtotal = sum(item['price'] * item['quantity'] for item in updated_items)
        updated_cart['itemCount'] = len(updated_items)
        updated_cart['subtotal'] = float(subtotal)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'cart': updated_cart,
                'itemsAdded': items_added,
                'itemsFailed': items_failed,
                'message': f'Added {len(items_added)} item(s)' + (f', {len(items_failed)} item(s) failed' if items_failed else '')
            }, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error adding to cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to add items to cart',
                'message': str(e)
            })
        }
