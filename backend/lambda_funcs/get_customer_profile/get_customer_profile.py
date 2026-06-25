import os
import json
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
CUSTOMERS_TABLE_NAME = os.environ.get('CUSTOMERS_TABLE_NAME')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    print(f"[DEBUG] GetCustomerProfile event: {json.dumps(event)}")
    
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
            
        table = dynamodb.Table(CUSTOMERS_TABLE_NAME)
        response = table.get_item(
            Key={
                'PK': f'CUSTOMER#{customer_id}',
                'SK': 'PROFILE'
            }
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({
                    'customer': None,
                    'message': f'Customer with ID {customer_id} not found. Please populate the Customers table with data.'
                })
            }
            
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'customer': response['Item']}, default=decimal_default)
        }
        
    except Exception as e:
        print(f"[ERROR] Error getting customer profile: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'error': 'Failed to get customer profile',
                'message': str(e)
            })
        }
