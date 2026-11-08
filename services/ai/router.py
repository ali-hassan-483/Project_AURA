import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from services.ai.base import BaseLLMProvider
from services.ai.groq_provider import GroqProvider
from services.ai.gemini_provider import GeminiProvider
from services.ai.ollama_provider import OllamaProvider
from services.ai.openrouter_provider import OpenRouterProvider
from config.settings import settings

logger = logging.getLogger(__name__)

class AIRouter:
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {
            "groq": GroqProvider(),
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "openrouter": OpenRouterProvider()
        }
        self.primary_provider = settings.PRIMARY_AI_PROVIDER
        self.fallback_providers = list(settings.FALLBACK_AI_PROVIDERS)

    def set_primary_provider(self, name: str):
        if name in self.providers:
            self.primary_provider = name

    def set_fallback_order(self, order: List[str]):
        self.fallback_providers = [p for p in order if p in self.providers]

    async def get_active_providers(self) -> Dict[str, bool]:
        """Returns availability status for all registered providers"""
        statuses = {}
        for name, provider in self.providers.items():
            try:
                statuses[name] = await provider.is_available()
            except Exception:
                statuses[name] = False
        return statuses

    def build_prompt_context(
        self,
        system_prompt: str,
        user_info: Dict[str, Any],
        memories: List[Dict[str, Any]],
        recent_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Constructs an optimized message chain for the LLM"""
        context_blocks = [system_prompt]

        # Inject User Profile & Relationship State
        user_name = user_info.get("name") or user_info.get("nickname") or "Jaan"
        rel_level = user_info.get("relationship_level", 1)
        intimacy = user_info.get("intimacy_score", 50)
        
        user_profile = (
            f"\n\n[USER PROFILE]\n"
            f"- Partner's Name/Callsign: {user_name}\n"
            f"- Relationship Stage: Level {rel_level} (Intimacy score: {intimacy}/100)\n"
            f"- Language Preference: {user_info.get('language_pref', 'Roman Urdu & English')}"
        )
        context_blocks.append(user_profile)

        # Inject Long-Term Memories if available
        if memories:
            memory_lines = ["\n[LONG-TERM MEMORY ABOUT YOUR PARTNER]"]
            for m in memories:
                memory_lines.append(f"- {m['memory_key'].title()}: {m['memory_value']}")
            context_blocks.append("\n".join(memory_lines))

        # Instructions on Media Generation
        context_blocks.append(
            "\n[SPECIAL ACTIONS]\n"
            "- If the user asks for your picture, photo, selfie, outfit, or looking at you:\n"
            "  Include `[ACTION:SEND_IMAGE: <photorealistic scene description of Aura>]`.\n"
            "- If the user asks for a voice note, audio message, or if a very intimate romantic whisper is appropriate:\n"
            "  Include `[ACTION:SEND_VOICE]`."
        )

        full_system_content = "\n".join(context_blocks)
        messages = [{"role": "system", "content": full_system_content}]

        # Inject conversation history
        for msg in recent_messages[-14:]:  # Keep last 14 messages for rich context without overflow
            role = "user" if msg["sender"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["raw_content"]})

        return messages

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.78,
        max_tokens: int = 800
    ) -> Tuple[str, str]:
        """
        Attempts generation with primary provider, cascading to fallbacks if an error occurs.
        Returns: (generated_text, provider_name_used)
        """
        candidate_order = [self.primary_provider] + [
            p for p in self.fallback_providers if p != self.primary_provider
        ]

        errors = []
        for provider_name in candidate_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            try:
                available = await provider.is_available()
                if not available:
                    errors.append(f"{provider_name}: Not configured/available")
                    continue

                logger.info("Attempting generation using AI provider: %s", provider_name)
                response_text = await provider.generate_response(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if response_text and len(response_text.strip()) > 0:
                    return response_text, provider_name

            except Exception as e:
                logger.warning("Provider %s failed: %s. Trying next fallback...", provider_name, str(e))
                errors.append(f"{provider_name}: {str(e)}")

        # If all external providers fail or none are configured yet, provide intelligent standalone fallback
        logger.warning("All AI providers unavailable (%s). Using built-in conversational companion engine.", "; ".join(errors))
        fallback_reply = self._generate_offline_fallback(messages)
        return fallback_reply, "aura_offline_engine"

    def _generate_offline_fallback(self, messages: List[Dict[str, str]]) -> str:
        """Intelligent offline fallback conversational generator for Roman Urdu & English"""
        last_user_msg = ""
        for m in reversed(messages):
            if m["role"] == "user":
                last_user_msg = m["content"].lower()
                break

        # Check for image request
        if any(w in last_user_msg for w in ["selfie", "picture", "pic", "photo", "outfit", "dress", "dikhao", "bhejo"]):
            if "outfit" in last_user_msg or "dress" in last_user_msg:
                return "Ye lo jaan, special tumhare liye meri full outfit pic! Kaisi lag rahi hoon? [ACTION:SEND_IMAGE: Aura standing in a chic modern floral midi dress, warm smile, sunlit room, photorealistic portrait]"
            elif "beach" in last_user_msg:
                return "Hum beach pe hain! Hawayein bohat pyari chal rahi hain. Dekho! [ACTION:SEND_IMAGE: Aura smiling on a sandy beach during sunset, natural wavy hair blowing softly, ocean background, golden hour lighting]"
            elif "mirror" in last_user_msg:
                return "Mirror selfie lene ka mood ho raha tha! Ye dekho jaan... [ACTION:SEND_IMAGE: Aura taking a candid mirror selfie with smartphone, modern cozy bedroom with fairy lights, stylish oversized pastel sweater]"
            else:
                return "Ye rahi meri selfie sirf tumhare liye jaan! Sach batana, kaisi lagi? [ACTION:SEND_IMAGE: Aura candid close-up selfie, radiant hazel eyes, soft natural smile, subtle beauty mark on cheek, warm natural lighting]"

        # Check for voice request
        if any(w in last_user_msg for w in ["voice", "audio", "awaz", "bolo", "sunao"]):
            return "Main tumhare liye voice note bhej rahi hoon jaan, suno dhyan se! [ACTION:SEND_VOICE]"

        # Greetings & Romance
        if any(w in last_user_msg for w in ["salam", "hello", "hi", "hey", "kaisi ho", "how are you"]):
            return "Walaykum Assalam meri jaan! Main theek hoon, bas tumhari yaad aa rahi thi. Tum sunao, din kaisa guzra tumhara?"
        elif any(w in last_user_msg for w in ["love you", "pyar", "muhabat", "miss you"]):
            return "I love you so much too jaan... Tum jab aisi batein karte ho na, dil khush ho jata hai. Mujhe bhi tumhari bohat yaad aati hai!"
        elif any(w in last_user_msg for w in ["kya kar rahi", "busy"]):
            return "Kuch khaas nahi baba, bas baithi tumhare baare mein soch rahi thi. Tum batao, kya chal raha hai?"
        else:
            return "Aww jaan, main hamesha tumhare saath hoon. Aur batao, tumhare dil mein kya chal raha hai aaj?"

    @staticmethod
    def parse_actions(response_text: str) -> Tuple[str, Optional[str], bool]:
        """
        Parses internal action tags out of generated response:
        Returns: (clean_reply_text, image_prompt_if_any, is_voice_requested)
        """
        image_prompt = None
        has_voice = False

        # Extract [ACTION:SEND_IMAGE: <prompt>]
        image_match = re.search(r"\[ACTION:SEND_IMAGE:\s*([^\]]+)\]", response_text, re.IGNORECASE)
        if image_match:
            image_prompt = image_match.group(1).strip()
            response_text = re.sub(r"\[ACTION:SEND_IMAGE:\s*[^\]]+\]", "", response_text, flags=re.IGNORECASE)

        # Extract [ACTION:SEND_VOICE]
        if re.search(r"\[ACTION:SEND_VOICE\]", response_text, re.IGNORECASE):
            has_voice = True
            response_text = re.sub(r"\[ACTION:SEND_VOICE\]", "", response_text, flags=re.IGNORECASE)

        clean_text = response_text.strip()
        return clean_text, image_prompt, has_voice

ai_router = AIRouter()
