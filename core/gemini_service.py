import requests
from django.conf import settings


class GroqBotService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GroqBotService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _ensure_initialized(self):
        if self._initialized:
            return
        self.api_key = getattr(settings, 'GROQ_API_KEY', None)
        self.conversation_histories = {}
        self.system_prompt = (
            "You are SBMS Assistant — AI for the Smart Beneficiary Mapping System, "
            "an Indian government scheme discovery platform. "
            "Help citizens find government benefit schemes, understand eligibility, "
            "guide them to apply, track applications, and raise grievances. "
            "Be helpful, empathetic, concise. Use simple language. Use markdown formatting."
        )
        self.model = "llama-3.1-8b-instant"
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

        if not self.api_key or str(self.api_key).startswith('your'):
            print("[GroqBotService] WARNING: GROQ_API_KEY is not set or is a placeholder.")
            self.api_key = None

        self._initialized = True

    def clear_chat(self, user_id):
        self._ensure_initialized()
        if user_id in self.conversation_histories:
            del self.conversation_histories[user_id]
        return True

    def send_message(self, user_id, message, user_info=""):
        self._ensure_initialized()

        if not self.api_key:
            return "⚠️ AI Chat is currently unavailable. GROQ_API_KEY is not configured."

        # Get or create conversation history for this user
        if user_id not in self.conversation_histories:
            self.conversation_histories[user_id] = []

        history = self.conversation_histories[user_id]

        # Add user message to history
        full_message = f"[{user_info}]\n\n{message}" if user_info else message
        history.append({"role": "user", "content": full_message})

        # Keep only last 10 messages to avoid token limits
        if len(history) > 10:
            history = history[-10:]
            self.conversation_histories[user_id] = history

        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt}
                ] + history,
                "max_tokens": 500,
                "temperature": 0.7,
            }

            resp = requests.post(
                self.api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                timeout=20
            )

            if resp.status_code == 429:
                return "⏳ AI rate limit reached. Please wait a moment and try again."
            elif resp.status_code in (401, 403):
                return "⚠️ Invalid GROQ_API_KEY. Please update it in Railway → Variables."
            elif resp.status_code != 200:
                print(f"[GroqBotService] API error {resp.status_code}: {resp.text[:200]}")
                return f"⚠️ AI service error (HTTP {resp.status_code}). Please try again."

            data = resp.json()
            choices = data.get('choices', [])
            if not choices:
                return "⚠️ No response from AI. Please try again."

            reply = choices[0]['message']['content'].strip()

            # Add assistant reply to history
            history.append({"role": "assistant", "content": reply})
            self.conversation_histories[user_id] = history

            return reply

        except requests.exceptions.Timeout:
            return "⏳ Request timed out. Please try again."
        except Exception as e:
            print(f"[GroqBotService] Error: {e}")
            if user_id in self.conversation_histories:
                del self.conversation_histories[user_id]
            return "⚠️ AI error. Please try again."


# Singleton instance — imported by views.py
gemini_bot_service = GroqBotService()
