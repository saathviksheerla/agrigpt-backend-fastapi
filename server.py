# listen for request(post) from whatsapp
# query the database for user's data
# send the user query and user data to the agent
# wait for the agent to respond
# send the agent's response back to whatsapp

from fastapi import FastAPI, Request
from pydantic import BaseModel
import json


app = FastAPI()

class WhatsAppRequest(BaseModel):
    user_id: str
    message: str

def query_database(user_id):
    # Placeholder for database query logic
    return {"name": "John Doe", "preferences": ["sports", "technology"]}

def send_to_agent(message, user_data):
    # Placeholder for agent communication logic
    # This function would send the message and user data to the agent and return the agent's response
    return f"Agent response based on message: '{message}' and user data: {user_data}"

@app.post("/whatsapp")
async def handle_whatsapp_request(req: WhatsAppRequest):
    # Step 1: Query the database for user's data
    # user_data =  query_database(request.user_id)

    # Step 2: Send the user query and user data to the agent
    # agent_response = send_to_agent(req.message, user_data)

    # Step 3: Send the agent's response back to WhatsApp
    return {"response": agent_response}