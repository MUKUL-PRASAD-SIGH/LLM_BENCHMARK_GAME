from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import io
from face_analyzer import analyzer

app = FastAPI(title="AI Avatar System API", version="0.1.0")

class FaceFeatures(BaseModel):
    jaw_width: float
    eye_size: float
    nose_length: float
    lip_thickness: float
    skin_tone: str

class AvatarConfig(BaseModel):
    user_id: int
    face_vector: FaceFeatures
    body_type: str = "athletic"
    hair_style: str = "short"
    hair_color: str = "black"
    outfit: str = "cyberpunk_jacket"
    accessory: str = "round_glasses"
    active_style: str = "realistic"

from database import db

@app.post("/api/v1/extract_features", response_model=FaceFeatures)
async def extract_facial_features(selfie: UploadFile = File(...)):
    """
    1. Upload a selfie image.
    2. Backend runs MediaPipe Face Mesh.
    3. Normalizes 3D landmarks into VRM blendshape morph targets.
    4. Returns parameters.
    """
    if not selfie.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    content = await selfie.read()
    features = analyzer.analyze_face(content)

    if "error" in features:
        raise HTTPException(status_code=422, detail=features["error"])

    # Returns normalized jaw_width, eye_size, nose_length, lip_thickness, skin_tone
    return features


@app.post("/api/v1/generate_avatar")
async def generate_avatar(config: AvatarConfig):
    """
    Binds the mapped face features to a pre-built base body template.
    Applies hair, clothes, and accessories.
    Stores the configuration in MongoDB (mocked here).
    """
    db.save_avatar(config.user_id, config.model_dump())
    
    # In production, this would queue a job to bake standard diffuse textures if necessary,
    # or just return the JSON config required over HTTP to the Unity Client.
    return {
        "status": "success",
        "message": f"Avatar generated and bound to {config.body_type} body template.",
        "config": db.get_avatar(config.user_id)
    }


@app.post("/api/v1/style_multiverse/{user_id}/{style}")
async def generate_styled_texture(user_id: int, style: str):
    """
    Style Multiverse Feature
    Given an already mapped avatar, generates a new texture or stylistic 3D skin
    using Stable Diffusion / InstantID. (Mocked response)
    
    Supported styles: cyberpunk, anime, warrior, cartoon, sci_fi_soldier
    """
    user_config = db.get_avatar(user_id)
    if not user_config:
        raise HTTPException(status_code=404, detail="Avatar config not found via User ID")
        
    valid_styles = ["cyberpunk", "anime", "warrior", "cartoon", "sci_fi_soldier", "realistic"]
    if style not in valid_styles:
        raise HTTPException(status_code=400, detail=f"Invalid style. Choose from {valid_styles}")
        
    user_config["active_style"] = style
    db.save_avatar(user_id, user_config)
    
    # Mock InstantID / Stable Diffusion execution
    generated_texture_url = f"https://s3.amazonaws.com/avatar-assets/{user_id}/{style}_diffuse.png"
    
    return {
        "status": "success",
        "message": f"Successfully stylized user {user_id}'s avatar into {style} mode.",
        "new_texture_url": generated_texture_url,
        "avatar_update": user_config
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
