# listen for request(post) from whatsapp
# query the database for user's data
# send the user query and user data to the agent
# wait for the agent to respond
# send the agent's response back to whatsapp

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import httpx
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# MongoDB Atlas connection string from environment variable
MONGODB_URL = os.getenv("MONGODB_URL")
# Agent service URL from environment variable
AGENT_URL = os.getenv("AGENT_URL")  # e.g., https://your-agent-service.com/process

# Global variables for MongoDB client and collections
client = None
db = None
users_collection = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    # Startup: Connect to MongoDB Atlas
    global client, db, users_collection
    client = AsyncIOMotorClient(MONGODB_URL)
    try:
        # Ping MongoDB to verify connection
        await client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas!")
        
        # Set database and collection references AFTER client is initialized
        db = client.agriculture
        users_collection = db.users
        print("Database and collection references set successfully!")
        
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
    
    yield
    
    # Shutdown: Close MongoDB connection
    if client:
        client.close()
        print("MongoDB connection closed")

# Initialize FastAPI app with lifespan handler
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("WHATSAPP_ORIGIN")],
    allow_methods=["GET", "POST"],
)

class WhatsAppRequest(BaseModel):
    """
    Request model for incoming WhatsApp messages
    """
    phoneNumber: str
    message: str

async def query_database(phoneNumber):
    """
    Query MongoDB for user data by phone number
    If user doesn't exist, create a new user with just the phone number
    
    Args:
        phoneNumber: User's phone number
        
    Returns:
        dict: User data from database (with datetime converted to string)
    """
    try:
        # Check if users_collection is initialized
        if users_collection is None:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        # Search for existing user by phone number
        user_data = await users_collection.find_one({"phoneNumber": phoneNumber})
        
        if user_data:
            # User exists, remove MongoDB's internal _id field
            user_data.pop('_id', None)
            # Convert datetime to ISO string for JSON serialization
            if 'createdAt' in user_data and isinstance(user_data['createdAt'], datetime):
                user_data['createdAt'] = user_data['createdAt'].isoformat()
            print(f"Found existing user with phone number: {phoneNumber}")
            return user_data
        else:
            # User doesn't exist, create new user
            created_at = datetime.utcnow()
            new_user = {
                "phoneNumber": phoneNumber,
                "createdAt": created_at
            }
            
            # Insert new user into database
            await users_collection.insert_one(new_user)
            print(f"Created new user with phone number: {phoneNumber}")
            
            # Return the new user data (without _id and datetime converted to string)
            new_user.pop('_id', None)
            new_user['createdAt'] = created_at.isoformat()
            return new_user
            
    except Exception as e:
        # Handle any database errors
        print(f"Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

async def send_to_agent(message, user_data):
    # return "i am the Agent"
    """
    Send user query and data to external agent service via POST request
    Wait for agent's response and return it
    
    Args:
        message: User's message/query
        user_data: User's data from database
        
    Returns:
        dict: Agent's response (returned as-is)
    """
    try:
        # Prepare payload for agent service
        payload = {
            "query": message,
            "user_data": user_data
        }
        
        # Use httpx async client to make POST request to agent
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                AGENT_URL,
                json=payload,
                timeout=120.0  # 120 second timeout
            )
            
            # Raise exception if request failed
            response.raise_for_status()
            
            # Return agent's JSON response as-is
            # return response.json()
            return response.text  # Return as text to allow flexibility in agent response format
            
    except httpx.TimeoutException:
        # Handle timeout errors
        raise HTTPException(status_code=504, detail="Agent service timeout")
    except httpx.HTTPError as e:
        # Handle HTTP errors from agent service
        raise HTTPException(status_code=502, detail=f"Agent service error: {str(e)}")
    except Exception as e:
        # Handle any other errors
        print(f"Agent communication error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error communicating with agent: {str(e)}")

@app.post("/whatsapp")
async def handle_whatsapp_request(req: WhatsAppRequest):
    """
    Main endpoint to handle incoming WhatsApp messages
    
    Flow:
    1. Receive request from WhatsApp
    2. Query database for user data (create if doesn't exist)
    3. Send query and user data to agent
    4. Wait for agent response
    5. Return agent response to WhatsApp
    
    Args:
        req: WhatsAppRequest containing phoneNumber and message
        
    Returns:
        dict: Agent's response (phoneNumber and message)
    """
    # Step 1: Query the database for user's data (creates user if not exists)
    user_data = await query_database(req.phoneNumber)

    # Step 2: Send the user query and user data to the agent
    agent_response = await send_to_agent(req.message, user_data)

    # Step 3: Send the agent's response back to WhatsApp
    # Return the agent's response as-is
    return {"phoneNumber": req.phoneNumber, "message": agent_response}