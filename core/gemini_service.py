import google.generativeai as genai
from django.conf import settings


class GeminiBotService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiBotService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _ensure_initialized(self):
        """Lazy initialization — runs on first use, not at import time."""
        if self._initialized:
            return

        self.api_key = getattr(settings, 'GEMINI_API_KEY', None)
        self.chats = {}
        self.system_instruction = (
            "You are SBMS Assistant — AI for the Smart Beneficiary Mapping System, "
            "an Indian government scheme discovery platform. Be helpful, brief, use markdown."
        )

        if not self.api_key or str(self.api_key).startswith('your'):
            print("[GeminiBotService] WARNING: GEMINI_API_KEY is not set.")
            self.api_key = None
        else:
            try:
                genai.configure(api_key=self.api_key)
            except Exception as e:
                print(f"[GeminiBotService] genai.configure error: {e}")
                self.api_key = None

        self._initialized = True

    def _get_chat(self, user_id):
        self._ensure_initialized()
        if not self.api_key:
            return None

        if user_id not in self.chats:
            # Try models in order
            for model_name in ['gemini-1.5-flash', 'gemini-pro']:
                try:
                    model = genai.GenerativeModel(
                        model_name,
                        system_instruction=self.system_instruction
                    )
                    self.chats[user_id] = model.start_chat(history=[])
                    break
                except Exception as e:
                    print(f"[GeminiBotService] Failed to init {model_name}: {e}")
                    continue

        return self.chats.get(user_id)

    def clear_chat(self, user_id):
        self._ensure_initialized()
        if user_id in self.chats:
            del self.chats[user_id]
        return True

    def send_message(self, user_id, message, user_info=""):
        chat = self._get_chat(user_id)
        if not chat:
            return "AI Chat is currently unavailable. Please check API configuration."

        try:
            full_prompt = f"[{user_info}]\n\nUser: {message}" if user_info else message
            response = chat.send_message(full_prompt)
            return response.text
        except Exception as e:
            err = str(e)
            print(f"[GeminiBotService] send_message error: {err}")
            if 'API key not valid' in err or 'API_KEY_INVALID' in err:
                return "⚠️ Invalid Gemini API Key. Please update GEMINI_API_KEY in Railway."
            if '429' in err or 'quota' in err.lower() or 'rate' in err.lower():
                return "⏳ API rate limit reached. Please wait a moment and try again."
            if user_id in self.chats:
                del self.chats[user_id]
            return "⚠️ AI error. Please try again."


gemini_bot_service = GeminiBotService()
