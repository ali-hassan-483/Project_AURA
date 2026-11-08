import os
import uuid
import urllib.parse
import logging
from pathlib import Path
from typing import Tuple, Optional
import httpx
from services.image.identity import identity_manager
from services.image.scenes import detect_scene_request
from config.settings import settings

logger = logging.getLogger(__name__)

GENERATED_IMG_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "images" / "generated"
GENERATED_IMG_DIR.mkdir(parents=True, exist_ok=True)

# Best free Pollinations models for photorealistic results
POLLINATIONS_MODELS = [
    "flux-realism",   # Best photorealism on Pollinations
    "flux",           # Fallback
]

class ImageGenerationService:
    def __init__(self):
        self.provider = settings.IMAGE_PROVIDER
        self.identity = identity_manager

    async def generate_character_image(
        self,
        scene_hint: str,
        seed_offset: int = 0
    ) -> Tuple[str, str, str]:
        """
        Generates a photorealistic consistent character image of Aura.
        Returns: (local_file_path, public_filename, composed_prompt)
        """
        scene_key, scene_desc, (width, height) = detect_scene_request(scene_hint)
        composed_prompt = self.identity.compose_prompt(scene_desc)
        seed = self.identity.get_generation_seed(seed_offset)

        file_id = f"aura_{scene_key}_{uuid.uuid4().hex[:8]}.jpg"
        save_path = GENERATED_IMG_DIR / file_id

        logger.info("Generating Aura image [%s] with seed %s...", scene_key, seed)

        image_bytes = None

        # Try each Pollinations model in order
        for model_name in POLLINATIONS_MODELS:
            if image_bytes:
                break
            try:
                encoded_prompt = urllib.parse.quote(composed_prompt)
                encoded_neg = urllib.parse.quote(self.identity.negative_anchor)
                pollinations_url = (
                    f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                    f"?width={width}&height={height}&seed={seed}"
                    f"&nologo=true&enhance=true&model={model_name}"
                    f"&negative={encoded_neg}"
                )

                logger.info("Trying Pollinations model: %s", model_name)
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    resp = await client.get(pollinations_url)
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        image_bytes = resp.content
                        logger.info("Image generated via Pollinations [%s] ✓", model_name)
                    else:
                        logger.warning("Pollinations [%s] responded %s, size=%s",
                                       model_name, resp.status_code, len(resp.content) if resp.content else 0)
            except Exception as e:
                logger.warning("Pollinations [%s] failed: %s", model_name, e)

        # Secondary Fallback: Local SD WebUI (if available on localhost:7860)
        if not image_bytes:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    check = await client.get("http://127.0.0.1:7860/docs")
                    if check.status_code == 200:
                        payload = {
                            "prompt": composed_prompt,
                            "negative_prompt": self.identity.negative_anchor,
                            "seed": seed,
                            "width": width,
                            "height": height,
                            "steps": 30,
                            "cfg_scale": 7.5
                        }
                        post_resp = await client.post(
                            "http://127.0.0.1:7860/sdapi/v1/txt2img",
                            json=payload, timeout=90.0
                        )
                        if post_resp.status_code == 200:
                            import base64
                            b64 = post_resp.json()["images"][0]
                            image_bytes = base64.b64decode(b64)
                            logger.info("Image generated via Local SD WebUI ✓")
            except Exception:
                pass

        # Save generated image
        if image_bytes:
            with open(save_path, "wb") as f:
                f.write(image_bytes)

            # Save first ever image as canonical reference
            canonical_path = Path(__file__).resolve().parent.parent.parent / "static" / "images" / "aura_canonical_reference.jpg"
            if not canonical_path.exists():
                with open(canonical_path, "wb") as f:
                    f.write(image_bytes)
        else:
            # Last resort placeholder
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (width, height), color=(30, 25, 35))
            draw = ImageDraw.Draw(img)
            draw.text((width // 4, height // 2), f"Aura: {scene_key.title()}", fill=(240, 210, 220))
            img.save(str(save_path), "JPEG")
            logger.warning("Placeholder generated for %s (network unavailable)", file_id)

        return str(save_path), file_id, composed_prompt


image_service = ImageGenerationService()
