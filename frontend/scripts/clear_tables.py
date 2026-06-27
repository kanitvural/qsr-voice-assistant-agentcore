import boto3
import sys

def clear_table(table_name):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(table_name)
    
    print(f"Scanning table {table_name}...")
    
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
            
        if not items:
            print(f"Table {table_name} is already empty.")
            return
            
        print(f"Found {len(items)} items. Deleting...")
        
        key_names = [k['AttributeName'] for k in table.key_schema]
        
        with table.batch_writer() as batch:
            for item in items:
                key = {k: item[k] for k in key_names}
                batch.delete_item(Key=key)
                
        print(f"✅ Successfully cleared {len(items)} items from {table_name}.\n")
    except Exception as e:
        print(f"❌ Error clearing {table_name}: {e}\n")

def main():
    print("Fetching table names from CloudFormation exports (us-east-1)...\n")
    client = boto3.client('cloudformation', region_name='us-east-1')
    
    table_exports = {
        'QSR-LocationsTableName': None,
        'QSR-MenuTableName': None,
        'QSR-CustomersTableName': None,
        'QSR-OrdersTableName': None,
        'QSR-CartsTableName': None
    }
    
    try:
        response = client.list_exports()
        exports = response.get('Exports', [])
        
        while 'NextToken' in response:
            response = client.list_exports(NextToken=response['NextToken'])
            exports.extend(response.get('Exports', []))
            
        for export in exports:
            if export['Name'] in table_exports:
                table_exports[export['Name']] = export['Value']
                
    except Exception as e:
        print(f"Error fetching CloudFormation exports: {e}")
        sys.exit(1)
        
    for export_name, table_name in table_exports.items():
        if table_name:
            clear_table(table_name)
        else:
            print(f"⚠️ Warning: Could not find table name for {export_name}")
            
    print("🎉 All done! You can now run seed_data.py to generate fresh data.")

if __name__ == "__main__":
    main()
