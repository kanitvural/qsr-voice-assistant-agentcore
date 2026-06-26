# QSR Voice Assistant powered by Amazon Bedrock AgentCore

<!-- Core Framework & Language -->
[![AWS CDK](https://img.shields.io/badge/AWS%20CDK-2.1127.0-orange.svg)](https://aws.amazon.com/cdk/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Amazon Bedrock](https://img.shields.io/badge/Amazon%20Bedrock-AgentCore-FF9900.svg)](https://aws.amazon.com/bedrock/)
[![Amazon Bedrock](https://img.shields.io/badge/Model-Nova%20Sonic%20v2-FF9900.svg)](https://aws.amazon.com/bedrock/)
[![MCP](https://img.shields.io/badge/MCP-Protocol-black.svg)](https://modelcontextprotocol.io/)
[![AWS Location](https://img.shields.io/badge/AWS%20Location-GeoPlaces-00A4A6.svg)](https://aws.amazon.com/location/)
[![React](https://img.shields.io/badge/React-Next.js-007ACC.svg)](https://nextjs.org/)

This project demonstrates a fully functional, highly conversational **Omnichannel Voice Ordering Assistant** for a Quick Service Restaurant (QSR) chain. Powered by **Amazon Nova Sonic v2** and **Amazon Bedrock AgentCore**, the assistant engages customers in natural, real-time voice conversations to take orders, upsell items, and locate the nearest branches using AWS Location Services.

---

## 📦 What Business Problem Does This Solve?

Traditional QSR ordering experiences (Drive-Thru speakers, mobile apps, and in-store kiosks) are often frictionless but highly impersonal. They lack the ability to intelligently upsell, remember past customer preferences, or dynamically adjust to the customer's real-time context.

**This AI Assistant acts as a hyper-personalized "Digital Cashier".**
Instead of tapping through a screen, the customer simply speaks naturally. The assistant knows who the customer is, remembers their past orders, knows exactly where they are physically located, and seamlessly orchestrates the entire checkout process.

If a customer says:
> *"I'm starving. I'll just have my usual order from yesterday, but add a large fries."*

The AI instantly uses its backend tools to look up the customer's order history, fetches the current menu prices, calculates the tax based on the nearest store's location, adds the items to the cart, and responds in less than a second via voice.

---

## 🔄 User Request Flow (Under the Hood)

The entire architecture is built on a highly secure, real-time streaming pipeline:

1. The user accesses the web application hosted on **Amazon S3 & CloudFront** from their browser or mobile device.
2. The user authenticates with **Amazon Cognito** using their username and password and receives JWT tokens (Access Token and ID Token).
3. The frontend exchanges the ID Token with the Cognito Identity Pool for temporary AWS credentials (Access Key, Secret Key, Session Token).
4. The frontend opens a **SigV4-signed WebSocket connection** to the **AgentCore Runtime** and sends the Access Token as the first message for identity verification.
5. The agent hosted in AgentCore Runtime validates the Access Token by calling the Cognito GetUser API and extracts the customer's verified name, email, and `customerId`.
6. AgentCore Runtime initializes the **Nova 2 Sonic** model on Amazon Bedrock and builds a personalized system prompt with the verified customer context.
7. AgentCore Runtime connects to **AgentCore Gateway** as an **MCP (Model Context Protocol) client** using SigV4 authentication and discovers the available tools.
8. The user speaks their order. The agent processes the voice input through Nova 2 Sonic and invokes tools asynchronously through the AgentCore Gateway using MCP.
9. AgentCore Gateway exposes the backend REST APIs as MCP tools, so that the agent can discover and invoke them by name. When the agent calls a tool, AgentCore Gateway forwards the request as a REST API call to the **API Gateway**, which routes it to the appropriate **Lambda function**. Lambda functions query **DynamoDB** tables and **AWS Location Services**.
10. Nova 2 Sonic generates a contextual voice response incorporating the tool results and streams it back to the user over the WebSocket connection.

---

## 📍 The Role of AWS Location Service (Location-Awareness)

A critical feature of this AI Assistant is its **Location-Awareness**. Since a QSR chain has hundreds of branches, the assistant needs to know exactly which branch to route the order to. AWS Location Service enables three incredible capabilities:

* **Geofencing (Drive-Thru vs. In-Store):** If the customer opens the app while sitting in their car in the drive-thru line, the system instantly detects they are 10 meters away from a specific branch. The AI automatically greets them with: *"I see you're at our Kadıköy branch! Should I send your order straight to the kitchen?"*
* **En Route / Pick-Up Calculation:** If the customer is driving, the AI can calculate a route and say: *"There is a branch right on your way to work, it's just a 2-minute detour. I'll send your coffee there so it's ready when you arrive."*
* **Dynamic Menu & Tax Calculation:** Different branches have different local taxes or menu availability. Finding the nearest branch ensures accurate pricing.

### 🧪 Synthetic Branch Generation (`seed_data.py`)
To make this demo incredibly realistic without requiring you to own a real restaurant chain, we included a special **`seed_data.py`** script. 
When you run the script, it asks for your city and your preferred restaurant type (e.g., "Burger"). It uses the **Amazon Geo Places API** to find *real* burger joints near your actual location and saves them into the DynamoDB `Locations` table as if they were your own chain's branches! This guarantees that when you test the voice assistant from your phone, it will seamlessly find real-world streets and locations near you.

---

## 🛠️ AWS Architecture & Services Used

* **Amazon Bedrock (Nova Sonic v2):** The core AI model natively handling speech-to-speech interaction with ultra-low latency.
* **Amazon Bedrock AgentCore:** Hosts the WebSocket Gateway and Runtime container, automatically orchestrating MCP tools and SigV4 authentication.
* **AWS Lambda & API Gateway:** Serverless compute layer executing business logic (AddToCart, PlaceOrder, GeocodeAddress).
* **Amazon DynamoDB:** Hosts 5 tables (`Customers`, `Locations`, `Menu`, `Orders`, `Carts`).
* **Amazon Cognito:** Secures the application via M2M and JWT tokens.
* **AWS Location Service (Geo Places):** Provides routing, geocoding, and nearest-location calculations.
* **AWS CDK (Cloud Development Kit):** Defines the entire infrastructure as code in Python.

---

## 🗄️ DynamoDB Tables

The project deploys 5 DynamoDB tables that act as the single source of truth:
1. **`QSR-Locations`**: Stores the GPS coordinates, addresses, and IDs of the restaurant branches.
2. **`QSR-Menu`**: Stores available items, prices, and allowed customizations (e.g., "No Onions", "Extra Cheese").
3. **`QSR-Customers`**: Stores customer profiles, loyalty tiers, and home locations.
4. **`QSR-Carts`**: A temporary table holding active shopping carts before checkout.
5. **`QSR-Orders`**: The historical ledger of all completed orders.

---

## 🚀 Deployment Instructions

### 1. Setup Your Environment
```bash
# Clone the repository
git clone https://github.com/<your-username>/qsr-voice-assistant-agentcore.git
cd qsr-voice-assistant-agentcore

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
npm install -g aws-cdk
```

### 2. Deploy the Infrastructure
The system uses AWS CDK. Deploy the backend and frontend stacks:
```bash
cdk deploy --all
```

### 3. Generate Synthetic Data
Once the deployment finishes, populate your DynamoDB tables with real-world locations near you:
```bash
python scripts/seed_data.py
```
*(The script will ask for your email to tie the test data to your Cognito account, and will use AWS Geo Places to find real locations near your address).*

---

## 🎯 Test the AI Assistant (Example Scenarios)

Once the data is seeded, open the frontend web application, log in, click the Microphone button, and try speaking these scenarios:

**🍔 1. The "Usual" Order**
> *"Hey! I want to order what I got yesterday."*
*(The AI will query DynamoDB for your past orders, read back the items, and ask for confirmation).*

**📍 2. Location Awareness & Upselling**
> *"I'm hungry, where is the nearest branch?"*
*(The AI will detect your GPS location, find the closest branch, and then naturally upsell you: "The closest one is on Main Street. Would you like to start an order? Maybe a burger and a shake?")*

**🛒 3. Cart Management**
> *"Add a Deluxe Burger with no onions, and a large fries. Actually, make that two large fries."*
*(The AI uses the MCP tools to update your DynamoDB cart dynamically).*
