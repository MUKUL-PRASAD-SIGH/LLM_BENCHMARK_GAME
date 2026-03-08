import os
import requests
import json
import base64

# Mock / Template for connecting to a GPU service (RunPod, AWS EC2, Replicate)
# running Stable Diffusion with ControlNet / IP-Adapter / InstantID.

STABLE_DIFFUSION_API_URL = os.getenv("SD_API_URL", "http://localhost:7860/sdapi/v1/txt2img")

STYLE_PROMPTS = {
    "realistic": "high detail, realistic photo, 8k uhd, dslr, soft lighting, high quality, masterpiece",
    "cyberpunk": "cyberpunk 2077 style, neon lighting, dark city, futuristic augmented reality, glowing wires, synthwave",
    "anime": "studio ghibli, makoto shinkai, highly detailed anime illustration, vibrant colors, cel shaded",
    "warrior": "dark fantasy, medieval knight armor, cinematic, grimdark, epic lighting",
    "cartoon": "pixar style, disney 3d cartoon, smooth shading, vibrant, stylized 3d render",
    "sci_fi_soldier": "halo master chief, space marine armor, sci-fi futuristic helmet, highly detailed techwear"
}

class StyleGenerator:
    def __init__(self):
        self.api_url = STABLE_DIFFUSION_API_URL

    def generate_style(self, user_face_b64: str, style_name: str, clothing: str, hair: str):
        """
        Takes the user's face (base64) and chosen style, then runs an image-to-image
        or IP-Adapter process to generate a customized stylized texture or portrait.
        """
        if style_name not in STYLE_PROMPTS:
            style_name = "realistic"

        # Construct a detailed generation prompt
        base_prompt = f"1boy, portrait, {clothing}, {hair} hair, {STYLE_PROMPTS[style_name]}"
        negative_prompt = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"

        # Example payload for Automatic1111 SD WebUI with ControlNet/IPAdapter
        payload = {
            "prompt": base_prompt,
            "negative_prompt": negative_prompt,
            "steps": 25,
            "width": 512,
            "height": 512,
            "sampler_name": "Euler a",
            "cfg_scale": 7,
            "alwayson_scripts": {
                "controlnet": {
                    "args": [
                        {
                            "input_image": user_face_b64,
                            "module": "ip-adapter_clip_sd15",
                            "model": "ip-adapter_sd15 [12345678]",
                            "weight": 0.8,
                            "resize_mode": "Crop and Resize",
                            "control_mode": "Balanced",
                            "pixel_perfect": True
                        }
                    ]
                }
            }
        }

        try:
            # Simulate an API call to the GPU worker cluster
            # response = requests.post(self.api_url, json=payload, timeout=60)
            # if response.status_code == 200:
            #     r = response.json()
            #     return r['images'][0]  # Base64 output image
            
            # Since we are not running a real massive GPU right now, we return a mock success
            print(f"--> [GPU CLUSTER] Generating {style_name} avatar texture...")
            return f"mock_base64_generated_{style_name}_texture"
            
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to AI generation cluster: {str(e)}")
            return None

style_gen = StyleGenerator()
