import google.generativeai as genai
from core.models import Scheme
import json

class GeminiBotService:
    _instance = None
    _chat_session = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # API Key provided by the user
        genai.configure(api_key="AIzaSyCSqxdFD2wDdUYfJbJxdAvsJmSnsvj4n6M")
        
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self._chat_session = self.model.start_chat(history=[])

    def get_scheme_context(self):
        # Pull top 50 schemes to provide some DB awareness without hitting context limits
        schemes = Scheme.objects.all()[:50]
        context_data = []
        for s in schemes:
            context_data.append(f"Scheme Name: {s.scheme_name}\nCategory: {s.benefit_type}\nState: {s.state}\nDescription: {s.description}")
        return "\n\n".join(context_data)

    def process_message(self, user_message):
        try:
            # Inject context implicitly into the message block
            context = self.get_scheme_context()
            prompt = (
                "You are the AI Assistant for the 'Smart Beneficiary Mapping System' (SBMS). "
                "Your primary goal is to help everyday citizens (who may not be tech-savvy) understand "
                "this system, find government benefit schemes they are eligible for, and guide them on how to apply. "
                "Explain things simply, be extremely polite, empathetic, and concise. "
                "If someone asks what this system is, explain that it's a platform to easily find and apply for government schemes based on their personal profile, track applications, and raise grievances if needed. "
                "Format your output using markdown for readability, with clear bullet points and simple language.\n\n"
                f"Available Government Schemes Context:\n{context}\n\n"
                f"Citizen's Request: {user_message}"
            )
            
            response = self._chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            print("Gemini API Error:", str(e))
            return "I apologize, but I am having trouble connecting to my knowledge base right now. Please try again in a moment."
