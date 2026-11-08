import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
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
        
        # Consistent Facial & Anatomical Anchors
        self.face_anchor = (
            "photorealistic authentic portrait of Aura, a stunning 21-year-old girl, "
            "radiant warm hazel-brown almond eyes, lustrous natural wavy dark brown hair, "
            "subtle beauty mark on left cheekbone, gentle natural lips, "
            "warm glowing South Asian skin tone with realistic fine skin pores, authentic skin texture"
        )
        
        # Photography Realism Anchors
        self.photography_style = (
            "captured on 85mm f/1.4 portrait lens, natural ambient cinematic lighting, "
            "realistic raw color grading, sharp focus on eyes, subtle film grain, "
            "award winning candid photography, ultra-realistic, photorealistic, 8k uhd"
        )
        
        # Universal Negative Anchors
        self.negative_anchor = (
            "ugly, deformed, disfigured, malformed limbs, extra fingers, mutated hands, "
            "poorly drawn face, bad eyes, crossed eyes, blur, bad anatomy, "
            "cartoon, 3d render, anime, illustration, video game, doll, mannequin, "
            "plastic skin, oversaturated, watermark, signature, duplicate face"
        )

    def compose_prompt(self, scene_description: str, pose_or_mood: Optional[str] = None) -> str:
        """
        Combines Aura's fixed identity anchors with the requested scene, outfit, and environment.
        """
        scene_elements = [self.face_anchor]
        
        if scene_description:
            scene_elements.append(scene_description.strip())
            
        if pose_or_mood:
            scene_elements.append(pose_or_mood.strip())
            
        scene_elements.append(self.photography_style)
        return ", ".join(scene_elements)

    def get_generation_seed(self, seed_offset: int = 0) -> int:
        """
        Calculates seed anchored around canonical seed to preserve bone structure
        while providing scene naturalness.
        """
        return self.seed_anchor + (seed_offset % 100)

    def save_canonical_reference(self, image_bytes: bytes) -> str:
        with open(self.reference_image_path, "wb") as f:
            f.write(image_bytes)
        logger.info("Saved canonical reference image at %s", self.reference_image_path)
        return str(self.reference_image_path)

identity_manager = IdentityManager()
