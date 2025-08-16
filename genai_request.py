import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

def initialize_chat():
    """
    Initializes the Gemini model and starts a new chat session.
    It securely reads the API key from environment variables.
    """
    try:
        # Correctly configure the API key from the environment variable
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise KeyError("GOOGLE_API_KEY not found in environment variables.")
        
        genai.configure(api_key=api_key)

    except KeyError as e:
        print(f"🔴 Error: {e}")
        print("Please make sure a .env file with your GOOGLE_API_KEY is present.")
        return None

    # Use a valid and current model name. 'gemini-1.5-flash' is fast and efficient.
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Start a new chat session. This object will remember the conversation.
    chat = model.start_chat(history=[])
    print("🤖 AI Chat Session Initialized.")
    return chat

def send_chat_message(chat_session, prompt):
    """
    Sends a message to the ongoing chat session and gets the response.
    """
    if not chat_session:
        return "Chat session is not initialized. Please check your API key."
    
    try:
        print(f"Sending to Gemini: '{prompt}'")
        # The history is automatically handled by the chat_session object.
        response = chat_session.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"🔴 An error occurred while sending the message: {e}")
        return "Sorry, I encountered an error communicating with the AI."