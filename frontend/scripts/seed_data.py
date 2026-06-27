import sys
import uuid
import json
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("boto3 is required. Run: pip install boto3")
    sys.exit(1)

# Initialize AWS clients (us-east-1 is required for consistency with our Bedrock setup)
REGION = 'us-east-1'
cfn_client = boto3.client('cloudformation', region_name=REGION)
cognito_client = boto3.client('cognito-idp', region_name=REGION)
geo_client = boto3.client('geo-places', region_name=REGION)
dynamodb_resource = boto3.resource('dynamodb', region_name=REGION)

MENU_CATEGORIES = {
    'burgers': [
        {'itemId': 'burger-classic', 'name': 'Classic Burger', 'description': 'Quarter pound beef patty with lettuce, tomato, onions, pickles', 'price': 5.99,
         'customizations': [
             {'id': 'no-onions', 'name': 'No Onions', 'price': 0, 'isRemoval': True},
             {'id': 'no-pickles', 'name': 'No Pickles', 'price': 0, 'isRemoval': True},
             {'id': 'extra-cheese', 'name': 'Extra Cheese', 'price': 0.50, 'isRemoval': False},
             {'id': 'bacon', 'name': 'Add Bacon', 'price': 1.50, 'isRemoval': False},
         ]},
        {'itemId': 'burger-deluxe', 'name': 'Deluxe Burger', 'description': 'Half pound beef patty with premium toppings', 'price': 8.99,
         'customizations': [
             {'id': 'no-onions', 'name': 'No Onions', 'price': 0, 'isRemoval': True},
             {'id': 'extra-cheese', 'name': 'Extra Cheese', 'price': 0.50, 'isRemoval': False},
         ]},
    ],
    'chicken': [
        {'itemId': 'chicken-sandwich', 'name': 'Chicken Sandwich', 'description': 'Crispy or grilled chicken breast with lettuce and mayo', 'price': 6.49,
         'customizations': [
             {'id': 'grilled', 'name': 'Grilled Chicken', 'price': 0, 'isRemoval': False},
             {'id': 'spicy', 'name': 'Spicy', 'price': 0, 'isRemoval': False},
             {'id': 'no-mayo', 'name': 'No Mayo', 'price': 0, 'isRemoval': True},
         ]},
        {'itemId': 'chicken-tenders', 'name': 'Chicken Tenders', 'description': '4 piece crispy chicken tenders', 'price': 7.99, 'customizations': []},
    ],
    'combos': [
        {'itemId': 'combo-burger', 'name': 'Burger Combo', 'description': 'Classic burger with fries and drink', 'price': 8.99,
         'customizations': [
             {'id': 'large-fries', 'name': 'Large Fries', 'price': 1.00, 'isRemoval': False},
             {'id': 'large-drink', 'name': 'Large Drink', 'price': 0.50, 'isRemoval': False},
         ]},
        {'itemId': 'combo-chicken', 'name': 'Chicken Combo', 'description': 'Chicken sandwich with fries and drink', 'price': 9.49,
         'customizations': [
             {'id': 'grilled', 'name': 'Grilled Chicken', 'price': 0, 'isRemoval': False},
         ]},
    ],
    'sides': [
        {'itemId': 'fries', 'name': 'French Fries', 'description': 'Crispy golden fries', 'price': 2.99, 'customizations': []},
        {'itemId': 'onion-rings', 'name': 'Onion Rings', 'description': 'Crispy battered onion rings', 'price': 3.49, 'customizations': []},
    ],
    'drinks': [
        {'itemId': 'soda', 'name': 'Fountain Drink', 'description': 'Choice of Coke, Sprite, or Dr Pepper', 'price': 1.99, 'customizations': []},
        {'itemId': 'shake', 'name': 'Milkshake', 'description': 'Vanilla, chocolate, or strawberry', 'price': 3.99, 'customizations': []},
    ],
}

def header(text):
    print(f"\n\033[34m{'='*80}\033[0m")
    print(f"\033[34m  {text}\033[0m")
    print(f"\033[34m{'='*80}\033[0m\n")

def info(text): print(f"\033[36mℹ️  {text}\033[0m")
def ok(text): print(f"\033[32m✅ {text}\033[0m")
def fail(text): print(f"\033[31m❌ {text}\033[0m")
def warn(text): print(f"\033[33m⚠️  {text}\033[0m")

def get_cloudformation_exports():
    info("Fetching table names and User Pool ID from CloudFormation exports...")
    paginator = cfn_client.get_paginator('list_exports')
    exports = {}
    for page in paginator.paginate():
        for export in page['Exports']:
            exports[export['Name']] = export['Value']
    
    required = ['QSR-LocationsTableName', 'QSR-CustomersTableName', 'QSR-MenuTableName', 'QSR-OrdersTableName', 'QSR-UserPoolId']
    missing = [req for req in required if req not in exports]
    if missing:
        fail(f"Missing required CloudFormation exports: {', '.join(missing)}")
        sys.exit(1)
        
    ok("Successfully loaded AWS Configuration.")
    return exports

def get_customer_info(exports):
    user_pool_id = exports['QSR-UserPoolId']
    while True:
        email = input("\033[36mEnter your registered email address (or leave blank for the default test account): \033[0m").strip()
        
        if not email:
            info("Using default CDK dummy AppUser...")
            customer_id = exports.get('QSR-AppUserCustomerId', 'cust-default')
            name = exports.get('QSR-AppUserName', 'Admin User')
            email = exports.get('QSR-AppUserEmail', 'admin@example.com')
            ok(f"Found Default Customer: {name} ({customer_id})")
            return customer_id, name, email
            
        try:
            response = cognito_client.list_users(
                UserPoolId=user_pool_id,
                Filter=f'email = "{email}"'
            )
            users = response.get('Users', [])
            if not users:
                fail(f"User with email '{email}' not found! Please try again.")
                continue
                
            user = users[0]
            attrs = {attr['Name']: attr['Value'] for attr in user.get('Attributes', [])}
            customer_id = attrs.get('custom:customerId')
            name = attrs.get('name', 'Unknown User')
            
            if not customer_id:
                fail("User found but 'custom:customerId' is missing. Please enter a valid user.")
                continue
                
            ok(f"Found Real Customer: {name} ({customer_id})")
            return customer_id, name, email
            
        except Exception as e:
            fail(f"Cognito Error: {e}")

def geocode_address(address):
    try:
        response = geo_client.geocode(
            QueryText=address,
            MaxResults=1
        )
        items = response.get('ResultItems', [])
        if items and 'Position' in items[0]:
            # geo-places returns [longitude, latitude]
            lon, lat = items[0]['Position']
            return lat, lon
        return None
    except Exception as e:
        fail(f"Geocoding Error: {e}")
        return None

def search_restaurants(lat, lon, business_name):
    try:
        radius_meters = 100 * 1609 # 100 miles
        response = geo_client.search_text(
            QueryText=business_name,
            Filter={
                'Circle': {
                    'Center': [lon, lat],
                    'Radius': radius_meters
                }
            },
            MaxResults=15
        )
        return response.get('ResultItems', [])
    except Exception as e:
        fail(f"AWS Geo Places API Error: {e}")
        return []

def generate_location_data(place, business_name):
    pos = place.get('Position', [0, 0])
    addr = place.get('Address', {})
    place_id = place.get('PlaceId', str(uuid.uuid4()))
    title = place.get('Title', 'Unknown Location')
    
    # Extract address parts safely
    country = addr.get('Country', {}).get('Name') if isinstance(addr.get('Country'), dict) else addr.get('Country')
    region = addr.get('Region', {}).get('Name') if isinstance(addr.get('Region'), dict) else addr.get('Region')
    
    location_id = place_id.replace('-', '').replace('_', '')[:12].lower()
    
    return {
        'PK': f"LOCATION#{location_id}",
        'locationId': location_id,
        'placeId': place_id,
        'name': title,
        'businessName': business_name,
        'address': addr.get('Label', title),
        'city': addr.get('Locality', ''),
        'state': region or '',
        'zipCode': addr.get('PostalCode', ''),
        'country': country or '',
        'latitude': str(pos[1]),
        'longitude': str(pos[0]),
        'phone': f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
        'isActive': True,
        'createdAt': datetime.utcnow().isoformat() + "Z"
    }

def generate_customer_profile(customer_id, name, email, lat, lon):
    tiers = [('Bronze', random.randint(0, 499)), ('Silver', random.randint(500, 999)), ('Gold', random.randint(1000, 1999))]
    tier, points = random.choice(tiers)
    
    return {
        'PK': f"CUSTOMER#{customer_id}",
        'SK': 'PROFILE',
        'customerId': customer_id,
        'name': name,
        'email': email,
        'homeLatitude': str(lat),
        'homeLongitude': str(lon),
        'loyaltyTier': tier,
        'loyaltyPoints': points,
        'createdAt': datetime.utcnow().isoformat() + "Z"
    }

def generate_menu_items(location_id):
    items = []
    for category, cat_items in MENU_CATEGORIES.items():
        for item in cat_items:
            # Convert float prices in customizations to Decimal for DynamoDB compatibility
            customizations = []
            for cust in item.get('customizations', []):
                cust_copy = dict(cust)
                cust_copy['price'] = Decimal(str(cust['price']))
                customizations.append(cust_copy)
                
            items.append({
                'PK': f"LOCATION#{location_id}#ITEM#{item['itemId']}",
                'locationId': location_id,
                'itemId': item['itemId'],
                'name': item['name'],
                'description': item['description'],
                'price': Decimal(str(item['price'])),
                'category': [category, 'All Items'],
                'isAvailable': True,
                'isCombo': category == 'combos',
                'availableCustomizations': customizations,
                'createdAt': datetime.utcnow().isoformat() + "Z"
            })
    return items

def generate_orders(customer_id, locations, num_orders=5):
    if not locations:
        return []
        
    all_items = [item for cat in MENU_CATEGORIES.values() for item in cat]
    orders = []
    
    for _ in range(num_orders):
        loc = random.choice(locations)
        days_ago = random.randint(1, 30)
        hours_ago = random.randint(0, 23)
        order_time = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
        
        order_id = f"order-{uuid.uuid4().hex[:12]}"
        num_items = random.randint(1, 3)
        order_items = []
        subtotal = 0.0
        
        for _ in range(num_items):
            item = random.choice(all_items)
            num_custom = random.randint(0, min(2, len(item['customizations'])))
            selected_custom = random.sample(item['customizations'], num_custom)
            
            item_price = item['price'] + sum(c['price'] for c in selected_custom)
            order_customizations = []
            for cust in selected_custom:
                cust_copy = dict(cust)
                cust_copy['price'] = Decimal(str(cust['price']))
                order_customizations.append(cust_copy)
                
            order_items.append({
                'itemId': item['itemId'],
                'name': item['name'],
                'price': Decimal(str(item['price'])),
                'quantity': 1,
                'customizations': order_customizations
            })
            subtotal += item_price
            
        tax = round(subtotal * 0.08, 2)
        total = round(subtotal + tax, 2)
        ts = int(order_time.timestamp())
        
        orders.append({
            'PK': f"CUSTOMER#{customer_id}",
            'SK': f"ORDER#{order_id}#{ts}",
            'GSI1PK': f"LOCATION#{loc['locationId']}",
            'GSI1SK': f"ORDER#{ts}",
            'customerId': customer_id,
            'orderId': order_id,
            'locationId': loc['locationId'],
            'locationName': loc['name'],
            'items': order_items,
            'subtotal': Decimal(str(round(subtotal, 2))),
            'tax': Decimal(str(tax)),
            'total': Decimal(str(total)),
            'status': 'completed',
            'createdAt': order_time.isoformat() + "Z",
            'completedAt': (order_time + timedelta(minutes=20)).isoformat() + "Z"
        })
        
    return orders

def ingest_data(table_name, items):
    table = dynamodb_resource.Table(table_name)
    info(f"Writing {len(items)} items to {table_name}...")
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    ok(f"Successfully wrote {len(items)} items to {table_name}")

def main():
    header("QSR Ordering System - Synthetic Data Population")
    exports = get_cloudformation_exports()
    
    header("Step 1: Customer Info")
    customer_id, customer_name, customer_email = get_customer_info(exports)
    
    header("Step 2: Location Input")
    while True:
        country = input("\033[36mEnter country (e.g. Turkey, US, UK): \033[0m").strip()
        city = input("\033[36mEnter city (e.g. Ordu, Dallas): \033[0m").strip()
        
        if not country or not city:
            warn("Country and city cannot be empty.")
            continue
            
        address = f"{city}, {country}"
        info(f"Geocoding address: {address}...")
        coords = geocode_address(address)
        if coords:
            ok(f"Address found! Coordinates: {coords[0]}, {coords[1]}")
            user_lat, user_lon = coords
            break
        else:
            fail("Address not found, please try something else.")
            
    header("Step 3: Business Name")
    while True:
        business_name = input("\033[36mWhat type of restaurant are we looking for? (e.g. Burger, Pizza, Coffee): \033[0m").strip()
        if business_name:
            break
            
    header("Step 4: Location Discovery")
    info(f"Searching for '{business_name}' within 100 miles of '{address}'...")
    
    places = search_restaurants(user_lat, user_lon, business_name)
    if not places:
        fail("No locations found! Exiting script.")
        return
        
    ok(f"Found {len(places)} locations!")
    for idx, p in enumerate(places[:5]):
        print(f"  {idx+1}. {p.get('Title')} ({p.get('Address', {}).get('Label', '')})")
    if len(places) > 5:
        print(f"  ...and {len(places)-5} more locations.")
        
    header("Step 5: Generating Synthetic Data")
    locations = [generate_location_data(p, business_name) for p in places]
    ok(f"Generated {len(locations)} location records")
    
    customer_profile = generate_customer_profile(customer_id, customer_name, customer_email, user_lat, user_lon)
    ok("Generated customer profile")
    
    menu_items = []
    for loc in locations:
        menu_items.extend(generate_menu_items(loc['locationId']))
    ok(f"Generated {len(menu_items)} menu items")
    
    orders = generate_orders(customer_id, locations, 5)
    ok(f"Generated {len(orders)} sample orders")
    
    header("Step 6: DynamoDB Ingestion")
    ingest_data(exports['QSR-LocationsTableName'], locations)
    ingest_data(exports['QSR-CustomersTableName'], [customer_profile])
    ingest_data(exports['QSR-MenuTableName'], menu_items)
    ingest_data(exports['QSR-OrdersTableName'], orders)
    
    header("Complete!")
    ok("Congratulations! Real-world locations and mock orders have been successfully loaded into DynamoDB.")
    info("You can now use the voice assistant to ask for nearby locations, menus, or repeat your past orders! 🎉")

if __name__ == "__main__":
    main()
