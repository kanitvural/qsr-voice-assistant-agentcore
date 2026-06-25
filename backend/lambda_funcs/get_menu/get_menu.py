import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
MENU_TABLE_NAME = os.environ.get('MENU_TABLE_NAME')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] GetMenu event: {json.dumps(event)}")
    
    try:
        if event.get('queryStringParameters'):
            params = event['queryStringParameters']
        else:
            params = json.loads(event.get('body', '{}'))
            
        location_id = params.get('locationId')
        
        if not location_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'locationId parameter is required'})
            }
            
        table = dynamodb.Table(MENU_TABLE_NAME)
        # Using Query instead of Scan since PK is LOCATION#{locationId}#ITEM#{itemId}
        # In DynamoDB, if PK format is LOCATION#{locationId}#ITEM#{itemId}, a Query requires the exact PK.
        # Wait, if PK is literally "LOCATION#123#ITEM#456", then we cannot use begins_with on PK in a Query.
        # We must use Scan if there is no GSI on locationId, or if the original code used Scan with begins_with on PK.
        # Let's check original: "Scan with filter since PK format is LOCATION#{locationId}#ITEM#{itemId}"
        
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('PK').begins_with(f'LOCATION#{location_id}#ITEM#')
        )
        
        menu_items = response.get('Items', [])
        
        if not menu_items:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'menuItems': [],
                    'message': f'No menu items found for location {location_id}. Please populate the Menu table with data.'
                }, default=decimal_default)
            }
            
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'menuItems': menu_items}, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error getting menu: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to get menu',
                'message': str(e)
            })
        }
