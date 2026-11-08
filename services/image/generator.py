import os
import re
import uuid
import asyncio
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

# Standard browser headers to prevent Cloudflare/firewall blocking from datacenter IPs (like Render)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Free Pollinations models in order of quality
POLLINATIONS_MODELS = [
    "flux-realism",
    "sana",
    "",  # default model
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
        Generates a photorealistic consistent character image of Aylin.
        Returns: (local_file_path, public_filename, composed_prompt)
        """
        scene_key, scene_desc, (width, height) = detect_scene_request(scene_hint)
        composed_prompt = self.identity.compose_prompt(scene_desc)
        seed = self.identity.get_generation_seed(seed_offset)

        file_id = f"aylin_{scene_key}_{uuid.uuid4().hex[:8]}.jpg"
        save_path = GENERATED_IMG_DIR / file_id

        logger.info("Generating Aylin image [%s] with seed %s...", scene_key, seed)

        image_bytes = None

        # 0. Primary optional: HuggingFace FLUX.1-schnell (if HF_API_KEY configured)
        if settings.HF_API_KEY:
            try:
                hf_url = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
                hf_headers = {
                    "Authorization": f"Bearer {settings.HF_API_KEY}",
                    "Content-Type": "application/json"
                }
                async with httpx.AsyncClient(timeout=40.0) as client:
                    resp = await client.post(hf_url, headers=hf_headers, json={"inputs": composed_prompt})
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        image_bytes = resp.content
                        logger.info("Image generated via HuggingFace FLUX ✓")
            except Exception as e:
                logger.warning("HuggingFace generation failed: %s", e)

        # 1. Pollinations.ai (Free models with rate-limit auto-wait & retry)
        if not image_bytes:
            encoded_prompt = urllib.parse.quote(composed_prompt)
            encoded_neg = urllib.parse.quote(self.identity.negative_anchor)

            for model_name in POLLINATIONS_MODELS:
                if image_bytes:
                    break

                model_param = f"&model={model_name}" if model_name else ""
                pollinations_url = (
                    f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                    f"?width={width}&height={height}&seed={seed}"
                    f"&nologo=true{model_param}&negative={encoded_neg}"
                )

                try:
                    logger.info("Trying Pollinations with model='%s'...", model_name or "default")
                    async with httpx.AsyncClient(timeout=50.0, follow_redirects=True) as client:
                        resp = await client.get(pollinations_url, headers=BROWSER_HEADERS)

                        if resp.status_code == 200 and len(resp.content) > 5000:
                            image_bytes = resp.content
                            logger.info("Image generated via Pollinations [%s] ✓", model_name or "default")
                            break

                        # Handle 402 Free Rate Limit ("Retry after Xs")
                        if resp.status_code == 402:
                            wait_seconds = 5
                            try:
                                err_json = resp.json()
                                msg = err_json.get("error", {}).get("message", "")
                                match = re.search(r"Retry after (\d+)s", msg)
                                if match:
                                    wait_seconds = min(int(match.group(1)) + 1, 15)
                            except Exception:
                                pass

                            logger.info("Pollinations rate limit active. Waiting %ss then retrying...", wait_seconds)
                            await asyncio.sleep(wait_seconds)

                            # Retry once after cooling down
                            retry_resp = await client.get(pollinations_url, headers=BROWSER_HEADERS)
                            if retry_resp.status_code == 200 and len(retry_resp.content) > 5000:
                                image_bytes = retry_resp.content
                                logger.info("Image generated via Pollinations retry [%s] ✓", model_name or "default")
                                break

                        logger.warning("Pollinations [%s] returned status %s", model_name or "default", resp.status_code)
                except Exception as e:
                    logger.warning("Pollinations [%s] request failed: %s", model_name or "default", e)

        # 2. Secondary Fallback: Local SD WebUI (if user is running it locally on localhost:7860)
        if not image_bytes:
            try:
                async with httpx.AsyncClient(timeout=4.0) as client:
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

        # 3. Save or deliver image
        if image_bytes:
            with open(save_path, "wb") as f:
                f.write(image_bytes)

            # Also update canonical reference if not present
            canonical_path = Path(__file__).resolve().parent.parent.parent / "static" / "images" / "aylin_reference.jpg"
            if not canonical_path.exists():
                with open(canonical_path, "wb") as f:
                    f.write(image_bytes)
        else:
            # Fallback realistic placeholder if completely offline/blocked
            from PIL import Image as PILImage, ImageDraw
            img = PILImage.new("RGB", (width, height), color=(30, 24, 38))
            draw = ImageDraw.Draw(img)
            draw.text((width // 4, height // 2), f"Aylin: {scene_key.title()}", fill=(245, 215, 225))
            img.save(str(save_path), "JPEG")
            logger.warning("Placeholder image generated for %s (upstream APIs busy)", file_id)

        return str(save_path), file_id, composed_prompt


image_service = ImageGenerationService()
