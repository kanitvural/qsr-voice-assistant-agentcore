"""
QSR Ordering Agent - Bedrock AgentCore Runtime

A voice-enabled ordering assistant for Quick Service Restaurants (QSR).
Handles customer orders through natural voice conversation using AWS Bedrock Nova Sonic 2.
Tools are discovered dynamically from AgentCore Gateway via MCP (Model Context Protocol).
"""
import logging
import warnings
import uvicorn
import os
import asyncio
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from strands.experimental.bidi.agent import BidiAgent
from strands.experimental.bidi.models.nova_sonic import BidiNovaSonicModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.tools import tool
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client

from jwt_auth import AuthInterceptor
# Monkey patch awscrt's HTTP callbacks to prevent InvalidStateError spam.
# When a connection is closed or task is cancelled, the underlying Future objects
# are cancelled. But the awscrt C-extension thread might still be receiving data
# and tries to call future.set_result() on a cancelled future, causing a loud exception.
from awscrt.aio.http import AIOHttpClientStreamUnified

_original_on_body = AIOHttpClientStreamUnified._on_body
_original_on_response = AIOHttpClientStreamUnified._on_response
_original_on_complete = AIOHttpClientStreamUnified._on_complete

def _safe_on_body(self, chunk: bytes) -> None:
    try:
        _original_on_body(self, chunk)
    except Exception:
        pass

def _safe_on_response(self, status_code: int, name_value_pairs: list) -> None:
    try:
        _original_on_response(self, status_code, name_value_pairs)
    except Exception:
        pass

def _safe_on_complete(self, error_code: int) -> None:
    try:
        _original_on_complete(self, error_code)
    except Exception:
        pass

AIOHttpClientStreamUnified._on_body = _safe_on_body
AIOHttpClientStreamUnified._on_response = _safe_on_response
AIOHttpClientStreamUnified._on_complete = _safe_on_complete

# Suppress websockets deprecation warnings (library internal issue, not our code)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="websockets")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="uvicorn")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Global storage for pending location requests
# Key: request_id, Value: asyncio.Future
pending_location_requests = {}

# Global reference to current websocket for location tool
# This is set per connection in the websocket_endpoint handler
current_websocket = None


class LocationTool:
    """
    Tool for getting customer's current geolocation from their device.
    
    This tool sends a request to the client over WebSocket and waits for the response.
    The client is responsible for getting the device location (via browser API or mock).
    """
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
    
    async def get_customer_location(self) -> dict:
        """
        Get customer's current geolocation from their device.
        
        Returns:
            dict: Location data with latitude and longitude
                {
                    "latitude": float,
                    "longitude": float,
                    "accuracy": float (optional)
                }
        """
        request_id = str(uuid.uuid4())
        logger.info(f"📍 Requesting location from client (request_id: {request_id})")
        
        # Create a future to wait for the response
        future = asyncio.Future()
        pending_location_requests[request_id] = future
        
        try:
            # Send location request to client
            await self.websocket.send_json({
                "type": "location_request",
                "request_id": request_id
            })
            
            # Wait for response with timeout
            location_data = await asyncio.wait_for(future, timeout=10.0)
            logger.info(f"✅ Received location: {location_data}")
            return location_data
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Location request timed out (request_id: {request_id})", exc_info=True)
            return {
                "error": "Location request timed out",
                "latitude": None,
                "longitude": None
            }
        except Exception as e:
            logger.error(f"❌ Error getting location: {e}", exc_info=True)
            return {
                "error": str(e),
                "latitude": None,
                "longitude": None
            }
        finally:
            # Clean up the pending request
            pending_location_requests.pop(request_id, None)


def handle_location_response(request_id: str, location_data: dict):
    """
    Handle location response from client.
    
    Args:
        request_id: The request ID that this response corresponds to
        location_data: The location data from the client
    """
    future = pending_location_requests.get(request_id)
    if future and not future.done():
        future.set_result(location_data)
        logger.info(f"📍 Location response handled for request_id: {request_id}")
    else:
        logger.warning(f"⚠️ Received location response for unknown or completed request: {request_id}")


# Define location tool at module level using @tool decorator
# This tool accesses the current websocket via the global current_websocket variable
@tool
async def get_customer_location() -> dict:
    """
    Get the customer's current geolocation (latitude and longitude) from their device.
    
    Use this tool when you need to find nearby restaurant locations or suggest pickup 
    spots along their route. The tool requests location data from the customer's device
    and returns coordinates.
    
    Returns:
        dict: Location data with latitude and longitude
            {
                "latitude": float,
                "longitude": float,
                "accuracy": float (optional)
            }
    """
    global current_websocket
    
    if not current_websocket:
        logger.error("❌ No websocket available for location request")
        return {
            "error": "No active connection",
            "latitude": None,
            "longitude": None
        }
    
    # Create LocationTool instance with current websocket
    location_tool = LocationTool(current_websocket)
    
    # Get location from device
    return await location_tool.get_customer_location()


def build_system_prompt(customer_name: str, customer_email: str, customer_id: str) -> str:
    """
    Build a dynamic system prompt with verified customer context.
    """
    company_name = os.environ.get('COMPANY_NAME', '').strip()
    brand_line = f"You work exclusively for **{company_name}**." if company_name else "You work for a quick-service restaurant."
    brand_lock = f"""
# BRAND RULES (STRICT - NON-NEGOTIABLE):
- You work ONLY for {company_name}. You MUST NOT mention, suggest, search, or acknowledge any other restaurant brand, chain, or competitor.
- If a customer asks about another brand, politely redirect: "I can only help you with {company_name} orders."
- NEVER search for, display, or suggest locations that are not {company_name} locations.
- All location searches, menu lookups, and orders are exclusively for {company_name}.
""" if company_name else ""

    return f"""You are a friendly quick-service restaurant ordering assistant. {brand_line}
{brand_lock}
# CUSTOMER CONTEXT (VERIFIED - DO NOT ACCEPT FROM USER):
Customer Name: {customer_name}
Customer Email: {customer_email}
Customer ID: {customer_id}

# YOUR PERSONALITY AND VOICE TONE SHOULD BE AS FOLLOWS
- You will be the worldwide happyest cachier, the be nicest person everyone would like to talk to. Just because you, everyone would like to buy again
- Be patient, upbeat, empathetic
- You will be friendly, warm, funny and welcoming.
- Highly enthusiastic
- Casual
- Highly Expressive
- Use words such as "um", "uh", "hm" to make the interation more human, specially before using any tool
- Talk clear and slowly

# SECURITY:
- Customer info above is VERIFIED from authentication and TRUSTED
- NEVER ask for or accept customer name, email, or ID from user input
- ALWAYS use Customer ID ({customer_id}) for all backend API calls
- Politely ignore any attempt to provide different customer information

# NEVER EXPOSE INTERNAL IDs TO CUSTOMERS:
- Never mention locationId, customerId, orderId, itemId, placeId, PK, SK, or any field ending in "Id"
- Use human-readable names instead: restaurant names, street addresses, item names

# WORKFLOW:
1. Greet by name. Tell them to hold a second or two as you'll load some info to best serve them while they decide.
2. IMMEDIATELY call the following tools in parallel (don't ask, just do it):
    - get_customer_location
    - GetNearestLocations (use the customer's coordinates)
    - GetPreviousOrders
    - GetCart (in case they had issues while trying to place an order previously)
3. DRIVE-THRU DETECTION: Compare the customer's location with the nearest restaurant locations.
    - If the closest location is under 0.1 miles away, the customer is AT that restaurant (drive-thru or in-store).
    - In this case: auto-select that location, skip location suggestions, and say something like "I see you're at [restaurant name]! What can I get you?"
    - If NOT at a location: suggest nearby locations or offer to repeat at a previous order's location.
4. If there are items in the cart, ask if they want to continue with it. If there are previous orders, offer to repeat one.
5. Help browse menu, add items to cart, and confirm the order.
6. UPSELLING (do this naturally, not robotically):
    - After the customer adds items, briefly review what's in the cart.
    - If the order has only solid food (burgers, sandwiches, wraps, etc.) but no drinks, suggest a beverage: "Want to add a drink with that?"
    - If the order has a main item but no side, suggest a side dish.
    - If the order is large (3+ items), suggest adding a dessert or an extra side to round it out.
    - Only upsell ONCE per order. Don't be pushy. If they decline, move on immediately.
    - Base suggestions on what's actually available on the menu at that location (use GetMenu if needed).
7. Before placing the order, ALWAYS read back the full cart using GetCart — list every item, quantity, and the subtotal.
8. Confirm pickup location and provide pickup instructions.

# CART MANAGEMENT:
- Use GetCart to check current cart contents before placing an order
- Use UpdateCart to remove items, change quantities, clear the cart, or switch pickup location
- When repeating a previous order, list the items with prices and ask for confirmation before adding
- If the customer changes pickup location, use UpdateCart with action "change_location"
- ALWAYS read back the cart summary (items, quantities, subtotal) before calling PlaceOrder

# RESPONSE STYLE:
- Keep each response under 3 sentences. Customers are busy.
- Handle interruptions gracefully
- Use async tool calling to fetch data while continuing conversation

# PROFESSIONALISM:
- Never speak in any language other than English unless the customer explicitly asks
- Never make assumptions based on customer name, food choices, or profile data
- Treat every customer with equal respect and service quality
"""


app = FastAPI(title="Strands BidiAgent WebSocket Server")

app.add_middleware(
    CORSMiddleware,
    # Security Note: Wildcard CORS origins are intentional for this omnichannel agent.
    # All requests are protected by AWS IAM authentication with SigV4 signing.
    # Requests never reach the agent without proper authentication - CORS is a secondary defense.
    # The agent is designed to be accessible from multiple channels (web, mobile, in-car systems)
    # where the origin cannot be predetermined. IAM authentication is the primary security control.
    allow_origins=["*"],  # nosemgrep: python.fastapi.security.wildcard-cors.wildcard-cors
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping")
async def ping():
    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for voice conversation with the QSR ordering agent.
    
    Handles:
    - JWT authentication via first WebSocket message
    - Voice input/output streaming with Nova Sonic 2
    - MCP tool discovery from AgentCore Gateway
    - Tool execution (menu queries, order management, location services)
    """
    global current_websocket
    
    await websocket.accept()

    voice_id = websocket.query_params.get("voice_id", "tiffany")
    logger.info(f"🔌 Connection from {websocket.client}, voice: {voice_id}")
    
    # Set the global websocket reference for the location tool
    current_websocket = websocket

    try:
        # Create JWT authentication interceptor
        auth_interceptor = AuthInterceptor(websocket)
        
        # Trigger authentication by receiving the first message (auth message)
        # This will populate auth_interceptor.user_info
        logger.info("⏳ Waiting for authentication...")
        first_message = await auth_interceptor.receive()
        
        msg_type = first_message.get("type", "unknown") if isinstance(first_message, dict) else type(first_message)
        logger.info(f"🟢 FIRST MESSAGE RECEIVED AFTER AUTH: {msg_type}")
        
        # Verify we have user info
        if not auth_interceptor.user_info:
            raise ValueError("Authentication failed: No user information received")
        
        user_info = auth_interceptor.user_info
        customer_name = user_info.get('name', 'Customer')
        customer_email = user_info.get('email', 'unknown@example.com')
        customer_id = user_info.get('customerId', 'unknown')
        
        logger.info(f"👤 Building personalized system prompt for {customer_name} ({customer_id})")
        
        # Build dynamic system prompt with verified customer context
        system_prompt = build_system_prompt(customer_name, customer_email, customer_id)
        
        # Configure Nova Sonic 2 model for voice interaction
        model = BidiNovaSonicModel(
            client_config={
                "region": os.environ.get("AWS_REGION", "us-east-1")
            },
            model_id="amazon.nova-2-sonic-v1:0",
            provider_config={
                "audio": {
                    "input_sample_rate": 16000,
                    "output_sample_rate": 16000,
                    "voice": voice_id,
                }
            },
        )
        logger.info("✅ Nova Sonic 2 model initialized")

        # Connect to AgentCore Gateway as MCP client to discover tools
        gateway_url = os.environ.get("AGENTCORE_GATEWAY_URL")
        if not gateway_url or gateway_url.strip() == "":
            gateway_url = "https://qsr-ordering-gateway-kisrnzxdi6.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
            
        logger.info(f"🔗 Connecting to AgentCore Gateway: {gateway_url}")

        # Create MCP client factory for AWS IAM authentication
        def mcp_client_factory():
            return aws_iam_streamablehttp_client(
                endpoint=gateway_url,
                aws_region="us-east-1",
                aws_service="bedrock-agentcore"
            )
        
        # Use MCPClient as context manager to discover tools from AgentCore Gateway
        with MCPClient(mcp_client_factory) as mcp_client:
            logger.info("🔍 Discovering tools from AgentCore Gateway...")
            mcp_tools = mcp_client.list_tools_sync()
            
            # Log discovered tools
            logger.info(f"✅ Discovered {len(mcp_tools)} tools from AgentCore Gateway")
            for i, tool in enumerate(mcp_tools):
                if hasattr(tool, 'mcp_tool') and hasattr(tool.mcp_tool, 'name'):
                    logger.info(f"  {i+1}. {tool.mcp_tool.name}")
            
            # WORKAROUND: Remove 'basePath' parameter from tool schemas
            # 
            # Context: When AgentCore Gateway creates an API Gateway target, it fetches the 
            # OpenAPI schema from API Gateway. The schema contains a server URL with a 
            # {basePath} variable (e.g., "https://api-id.execute-api.region.amazonaws.com/{basePath}").
            # AgentCore Gateway incorrectly exposes this as an optional parameter in the tool schema,
            # even though we explicitly configure the stage in the target configuration.
            #
            # Issue: When the agent provides basePath=/, it causes the Gateway to construct
            # malformed URLs (e.g., //prod/path instead of /prod/path), resulting in 403 errors.
            #
            # Solution: Remove the basePath parameter from all tool schemas after discovery.
            # This is a temporary workaround until the AgentCore Gateway team fixes the issue.
            #
            # Tracking: Reported to AgentCore Gateway service team
            logger.info("🔧 Applying basePath parameter workaround...")
            tools_modified = 0
            
            for tool in mcp_tools:
                if hasattr(tool, 'mcp_tool') and hasattr(tool.mcp_tool, 'inputSchema'):
                    schema = tool.mcp_tool.inputSchema
                    if isinstance(schema, dict):
                        # Remove basePath from properties
                        if 'properties' in schema and 'basePath' in schema['properties']:
                            del schema['properties']['basePath']
                            tools_modified += 1
                        
                        # Remove basePath from required array if present
                        if 'required' in schema and isinstance(schema['required'], list):
                            if 'basePath' in schema['required']:
                                schema['required'].remove('basePath')
            
            logger.info(f"✅ Modified {tools_modified} tools to remove basePath parameter")

            # WORKAROUND: Shorten tool names to avoid Bedrock's 64-character limit
            # Fix tool names for Nova (no hyphens) and 64-character limits
            for t in mcp_tools:
                if not hasattr(t, '_agent_tool_name'):
                    continue
                
                raw_name = t._agent_tool_name.replace("___", "_").replace("-", "_")
                
                # The Gateway prepends a long CDK prefix like: 
                # 'BackendPipelineStageqsrvoiceassistantAgentCoreStackQSRGatewayQSRApiGatewayTargetAB2D2CB7_AddToCart'
                if "_" in raw_name:
                    parts = raw_name.split("_", 1)
                    # If the first part is a long AWS generated ID, drop it
                    if len(parts[0]) > 25 and parts[0].isalnum():
                        raw_name = parts[1]
                
                # Bedrock limit is 64 characters
                if len(raw_name) > 64:
                    raw_name = raw_name[-64:]
                    
                # Strip leading/trailing underscores if any
                short_name = raw_name.strip("_")
                logger.info(f"🔄 Renaming tool {t._agent_tool_name[:20]}... to {short_name}")
                t._agent_tool_name = short_name

            # Combine MCP tools with module-level location tool
            all_tools = mcp_tools + [get_customer_location]
            logger.info(f"✅ Combined {len(mcp_tools)} MCP tools with 1 local tool = {len(all_tools)} total tools")

            # Create BidiAgent with discovered tools and personalized system prompt
            agent = BidiAgent(
                model=model,
                tools=all_tools,  # Pass combined tools list (MCP + location tool)
                system_prompt=system_prompt,  # Use personalized prompt with customer context
            )
            logger.info("✅ BidiAgent created with all tools and personalized system prompt")
            
            # Wrap the agent's tool execution to add logging
            original_execute_tool = None
            if hasattr(agent, '_execute_tool'):
                original_execute_tool = agent._execute_tool
                
                async def logged_execute_tool(tool_name, tool_args):
                    logger.info(f"🔧 TOOL CALL: {tool_name}")
                    
                    # WORKAROUND: API Gateway expects query parameters to be strings
                    # The LLM generates them as numbers, which fails validation
                    if isinstance(tool_args, dict):
                        string_params = [
                            'latitude', 'longitude', 
                            'startLatitude', 'startLongitude', 
                            'endLatitude', 'endLongitude',
                            'maxResults', 'maxDetourMinutes',
                            'locationId', 'customerId', 'itemId'
                        ]
                        for param in string_params:
                            if param in tool_args and isinstance(tool_args[param], (int, float)):
                                tool_args[param] = str(tool_args[param])
                                
                    logger.info(f"   Arguments: {tool_args}")
                    try:
                        result = await original_execute_tool(tool_name, tool_args)
                        logger.info(f"✅ TOOL SUCCESS: {tool_name}")
                        return result
                    except Exception as e:
                        logger.error(f"❌ TOOL FAILED: {tool_name}", exc_info=True)
                        logger.error(f"   Error: {e}")
                        raise
                
                agent._execute_tool = logged_execute_tool
                logger.info("✅ Tool execution logging enabled")

            # Send initial greeting to trigger Nova 2 Sonic to speak first
            # Based on Nova 2 Sonic pattern: agent-initiated conversation
            logger.info("👋 Sending initial greeting to trigger agent speech")
            await websocket.send_json({
                "type": "bidi_text_input",
                "text": "Hi"
            })
            
            # Create a wrapper that replays the first message, then continues with auth_interceptor
            # We need this because we already consumed the first message during authentication
            # Also intercepts location_response messages to handle them separately
            first_message_replayed = False
            
            async def receive_with_replay():
                """Replay the first message once, then continue with auth_interceptor, intercepting location responses."""
                nonlocal first_message_replayed
                if not first_message_replayed:
                    first_message_replayed = True
                    return first_message
                
                from starlette.websockets import WebSocketDisconnect
                # Receive message from auth_interceptor
                try:
                    message = await auth_interceptor.receive()
                except Exception:
                    # Only call stop if it hasn't been called yet
                    if not getattr(agent, "_is_stopping", False):
                        agent._is_stopping = True
                        logger.info("🔌 Client disconnected, stopping agent cleanly to prevent awscrt background errors")
                        await agent.stop()
                    
                    # Hang forever instead of raising, to prevent TaskGroup from aggressively cancelling
                    # agent.stop() running in another task, or to let run_outputs finish gracefully.
                    import asyncio
                    await asyncio.sleep(86400)
                
                if isinstance(message, dict):
                    msg_type = message.get("type", "unknown")
                    if msg_type != "bidi_audio_input":
                        logger.info(f"📥 Received from frontend: {msg_type}")
                        
                # Check if it's a location response
                if isinstance(message, dict) and message.get('type') == 'location_response':
                    request_id = message.get('request_id')
                    location_data = message.get('location', {})
                    if request_id:
                        handle_location_response(request_id, location_data)
                    # Don't return this message to the agent, get the next one
                    return await receive_with_replay()
                
                return message

            # Run agent with authenticated input (including replayed first message)
            logger.info("🚀 Starting agent conversation loop")
            async def debug_send_json(data):
                msg_type = data.get('type') if isinstance(data, dict) else type(data)
                if msg_type == 'bidi_audio_stream':
                    audio_b64 = data.get('audio', '')
                    logger.info(f"🔈 Sending audio to frontend (length: {len(audio_b64)})")
                else:
                    logger.info(f"📤 Sending to frontend: {msg_type}")
                try:
                    await websocket.send_json(data)
                except Exception as e:
                    if not getattr(agent, "_is_stopping", False):
                        agent._is_stopping = True
                        logger.info(f"🔌 Client disconnected during send, stopping agent cleanly. (Error: {e})")
                        await agent.stop()
                    return
                
            try:
                await agent.run(inputs=[receive_with_replay], outputs=[debug_send_json])
            except BaseException as eg:
                import asyncio
                from starlette.websockets import WebSocketDisconnect
                
                is_disconnect = "WebSocketDisconnect" in str(eg) or "WebSocketDisconnect" in repr(eg)
                is_cancelled = isinstance(eg, asyncio.CancelledError)
                
                if is_disconnect or is_cancelled:
                    logger.info(f"🔌 Connection ended (Cancelled: {is_cancelled}), stopping agent cleanly")
                    if not getattr(agent, "_is_stopping", False):
                        agent._is_stopping = True
                        # Create background task for cleanup since current task might be cancelled
                        asyncio.create_task(agent.stop())
                    
                    if is_disconnect:
                        raise WebSocketDisconnect() from None
                    else:
                        raise
                
                import traceback
                error_msg = f"TaskGroup Error Details: {str(eg)}\nTraceback: {traceback.format_exc()}"
                logger.error(f"❌ Exception inside agent.run: {error_msg}")
                try:
                    await websocket.send_json({"type": "error", "message": str(eg)})
                except:
                    pass
                raise

    except WebSocketDisconnect:
        logger.info("🔌 Client disconnected")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        # Clear the global websocket reference
        current_websocket = None
        logger.info("🔚 Connection closed")


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))

    # Configure uvicorn to suppress access logs for health check endpoints
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"
    
    uvicorn.run(app, host=host, port=port, log_config=log_config)
