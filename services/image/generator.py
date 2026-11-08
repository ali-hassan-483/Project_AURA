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

class ImageGenerationService:
    def __init__(self):
        self.provider = settings.IMAGE_PROVIDER
        self.model = settings.IMAGE_MODEL
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

        # 1. Primary: Pollinations.ai (Free Flux / SDXL, zero-cost)
        try:
            encoded_prompt = urllib.parse.quote(composed_prompt)
            encoded_neg = urllib.parse.quote(self.identity.negative_anchor)
            pollinations_url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?width={width}&height={height}&seed={seed}&nologo=true&model={self.model}"
                f"&negative={encoded_neg}"
            )
            
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                resp = await client.get(pollinations_url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    image_bytes = resp.content
                    logger.info("Image generated successfully via Pollinations AI.")
                else:
                    logger.warning("Pollinations responded with status %s", resp.status_code)
        except Exception as e:
            logger.warning("Pollinations generation failed: %s", e)

        # 2. Secondary Fallback: Local SD WebUI (if available on localhost:7860)
        if not image_bytes:
            try:
                local_sd_url = "http://127.0.0.1:7860/sdapi/v1/txt2img"
                async with httpx.AsyncClient(timeout=5.0) as client:
                    check = await client.get("http://127.0.0.1:7860/docs")
                    if check.status_code == 200:
                        payload = {
                            "prompt": composed_prompt,
                            "negative_prompt": self.identity.negative_anchor,
                            "seed": seed,
                            "width": width,
                            "height": height,
                            "steps": 25,
                            "cfg_scale": 7.0
                        }
                        post_resp = await client.post(local_sd_url, json=payload, timeout=60.0)
                        if post_resp.status_code == 200:
                            import base64
                            b64 = post_resp.json()["images"][0]
                            image_bytes = base64.b64decode(b64)
                            logger.info("Image generated successfully via Local SD WebUI.")
            except Exception:
                pass

        # 3. Save generated image
        if image_bytes:
            with open(save_path, "wb") as f:
                f.write(image_bytes)

            # Check if canonical reference exists, if not initialize it
            canonical_path = Path(__file__).resolve().parent.parent.parent / "static" / "images" / "aura_canonical_reference.jpg"
            if not canonical_path.exists():
                with open(canonical_path, "wb") as f:
                    f.write(image_bytes)
        else:
            # Fallback: create placeholder realistic reference file if network was unavailable
            from PIL import Image, ImageDraw, ImageFont
            img = Image.new("RGB", (width, height), color=(30, 25, 35))
            draw = ImageDraw.Draw(img)
            draw.text((width // 4, height // 2), f"Aura Portrait: {scene_key.title()}", fill=(240, 210, 220))
            img.save(str(save_path), "JPEG")
            logger.warning("Fallback placeholder generated for %s", file_id)

        return str(save_path), file_id, composed_prompt

image_service = ImageGenerationService()
