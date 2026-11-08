import re
from typing import Dict, Any, Tuple

# Predefined contextual templates matching user command requests
SCENE_PRESETS = {
    "selfie": {
        "description": "taking a candid cute selfie, looking directly into the smartphone camera, genuine happy expression, soft indoor bedroom lighting",
        "shot_type": "close-up selfie angle",
        "aspect": (768, 1024)
    },
    "mirror_selfie": {
        "description": "standing in front of a modern full-length bedroom mirror taking a mirror selfie with her phone, modern cozy aesthetic room with fairy lights in the background",
        "shot_type": "medium mirror selfie",
        "aspect": (768, 1024)
    },
    "outfit": {
        "description": "standing full body shot showing off a stylish contemporary floral embroidered dress, elegant posture, soft natural daylight, minimalist modern apartment interior",
        "shot_type": "full body fashion shot",
        "aspect": (768, 1152)
    },
    "beach": {
        "description": "walking along a golden sand beach at sunset, sea breeze gently moving her wavy brown hair, ocean waves and orange sky in the background, happy relaxed smile",
        "shot_type": "wide outdoor portrait",
        "aspect": (1024, 768)
    },
    "dress": {
        "description": "wearing a breathtaking elegant emerald green evening gown, graceful standing pose, delicate gold jewelry, luxurious softly lit lounge environment",
        "shot_type": "medium full body portrait",
        "aspect": (768, 1024)
    },
    "smiling": {
        "description": "warm heartfelt laughter, crinkling eyes, joyful candid radiant smile, morning sunlight streaming through a window",
        "shot_type": "candid close-up",
        "aspect": (768, 1024)
    },
    "cafe": {
        "description": "sitting by an outdoor cafe table in autumn, holding a warm ceramic cup of coffee, cozy knit cardigan, warm cafe bokeh background",
        "shot_type": "medium portrait",
        "aspect": (768, 1024)
    },
    "cozy_rainy": {
        "description": "curled up on a window sill on a rainy afternoon, raindrops on the window glass, wearing an oversized beige sweater, peaceful thoughtful expression",
        "shot_type": "cinematic indoor portrait",
        "aspect": (768, 1024)
    }
}

def detect_scene_request(text: str) -> Tuple[str, str, Tuple[int, int]]:
    """
    Analyzes user text or LLM action prompt to identify best scene preset.
    Returns: (scene_key, detailed_description, (width, height))
    """
    lower = text.lower()
    
    if "mirror" in lower:
        key = "mirror_selfie"
    elif "beach" in lower or "samandar" in lower:
        key = "beach"
    elif "outfit" in lower or "full picture" in lower or "dress" in lower or "suit" in lower:
        key = "outfit" if "outfit" in lower else "dress"
    elif "smile" in lower or "smiling" in lower or "hanso" in lower:
        key = "smiling"
    elif "cafe" in lower or "coffee" in lower or "chai" in lower:
        key = "cafe"
    elif "rain" in lower or "barish" in lower or "cozy" in lower:
        key = "cozy_rainy"
    elif "selfie" in lower or "pic" in lower or "photo" in lower or "tasweer" in lower:
        key = "selfie"
    else:
        # Default to selfie / close-up
        key = "selfie"

    preset = SCENE_PRESETS[key]
    return key, preset["description"], preset["aspect"]
