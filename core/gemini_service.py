import os
import google.generativeai as genai
from django.conf import settings
from .models import Scheme

class GeminiBotService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiBotService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        self.system_instruction = (
            "You are SBMS Assistant — AI for the Smart Beneficiary Mapping System, "
            "an Indian government scheme discovery platform. Be helpful, brief, use markdown."
        )
        self.chats = {}

        if not self.api_key or self.api_key == 'your_actual_key' or self.api_key.startswith('your_'):
            print("[GeminiBotService] WARNING: GEMINI_API_KEY is not set or is a placeholder.")
            self.api_key = None
        
        self.system_instruction = (
            "You are SBMS Assistant — AI for the Smart Beneficiary Mapping System, "
            "an Indian government scheme discovery platform. Be helpful, brief, use markdown."
        )
        self.chats = {}

    def _get_chat(self, user_id):
        if not self.api_key:
            return None
            
        if user_id not in self.chats:
            try:
                model = genai.GenerativeModel(
                    'gemini-2.0-flash-lite',
                    system_instruction=self.system_instruction
                )
                self.chats[user_id] = model.start_chat(history=[])
            except Exception as e:
                print(f"Error initializing chat for user {user_id}: {e}")
                return None
                
        return self.chats[user_id]

    def clear_chat(self, user_id):
        if user_id in self.chats:
            del self.chats[user_id]
        return True

    def send_message(self, user_id, message, user_info=""):
        chat = self._get_chat(user_id)
        if not chat:
            return "AI Chat is currently unavailable. Please check API configuration."

        try:
            full_prompt = message
            if user_info:
                full_prompt = f"[{user_info}]\n\nUser: {message}"

            response = chat.send_message(full_prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API Error: {e}")
            if "API key not valid" in str(e):
                return "Authentication error: Invalid API Key. Please contact administrator."
            return "I ran into an error processing your request. Please try again."

gemini_bot_service = GeminiBotService()
