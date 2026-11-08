import os
import logging
from pathlib import Path
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

REFERENCE_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "images"
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

class IdentityManager:
    """
    Maintains Aura's permanent visual identity, facial features, seed anchors,
    and photographic rendering parameters across all image generations.
    """
    def __init__(self):
        self.name = "Aura"
        self.age = 21
        self.seed_anchor = settings.IMAGE_SEED
        self.reference_image_path = REFERENCE_DIR / "aura_canonical_reference.jpg"

        # --- Core Identity (concise = better Pollinations results) ---
        self.face_anchor = (
            "RAW photo, (photorealistic:1.4), beautiful 21-year-old South Asian woman, "
            "warm hazel brown almond eyes, long natural wavy dark brown hair, "
            "subtle beauty mark left cheek, soft natural lips, "
            "flawless warm golden skin, real skin texture and pores"
        )

        # --- Photography Style ---
        self.photography_style = (
            "shot on Sony A7R, 85mm f/1.4 lens, shallow depth of field, "
            "cinematic natural lighting, sharp eyes in focus, "
            "(ultra realistic:1.3), 8k uhd, film grain, award winning photo"
        )

        # --- Negative Anchors (critical for quality) ---
        self.negative_anchor = (
            "ugly, deformed, disfigured, poorly drawn face, bad anatomy, "
            "extra fingers, mutated hands, missing limbs, blurry, "
            "cartoon, anime, illustration, 3d render, cgi, painting, "
            "watermark, text, signature, lowres, bad proportions, "
            "cross-eyed, asymmetric eyes, plastic skin, oversaturated"
        )

    def compose_prompt(self, scene_description: str, pose_or_mood: Optional[str] = None) -> str:
        """
        Combines Aura's fixed identity anchors with the requested scene.
        Order: quality tags → face → scene → photography style
        """
        parts = [
            self.face_anchor,
            scene_description.strip() if scene_description else "",
            self.photography_style
        ]
        if pose_or_mood:
            parts.insert(2, pose_or_mood.strip())

        # Remove empty parts
        parts = [p for p in parts if p]
        return ", ".join(parts)

    def get_generation_seed(self, seed_offset: int = 0) -> int:
        """
        Seed anchored to canonical seed to preserve bone structure
        while providing scene naturalness variation (offset max ±50).
        """
        return self.seed_anchor + (seed_offset % 50)

    def save_canonical_reference(self, image_bytes: bytes) -> str:
        with open(self.reference_image_path, "wb") as f:
            f.write(image_bytes)
        logger.info("Saved canonical reference image at %s", self.reference_image_path)
        return str(self.reference_image_path)


identity_manager = IdentityManager()
