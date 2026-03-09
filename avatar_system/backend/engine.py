import os
import urllib.request
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import base64
import insightface
from insightface.app import FaceAnalysis

app = FastAPI(title="Pro Avatar Gen - Deep Learning Engine")

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
SWAPPER_MODEL_PATH = os.path.join(MODELS_DIR, 'inswapper_128.onnx')
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# We will initialize the models lazily or on startup
face_app = None
swapper = None

def download_swapper_model():
    """Helper to safely download the inswapper_128.onnx model if not present."""
    if os.path.exists(SWAPPER_MODEL_PATH):
        return

    print("Downloading inswapper_128.onnx... This will take a while (~540MB).")
    url = "https://huggingface.co/facefusion/facefusion-assets/resolve/main/inswapper_128.onnx"
    
    try:
        # We download in chunks to track progress
        req = urllib.request.urlopen(url)
        total_size = int(req.headers.get('content-length', 0))
        
        with open(SWAPPER_MODEL_PATH, 'wb') as f:
            downloaded = 0
            block_size = 1024 * 1024 # 1MB chunks
            while True:
                buffer = req.read(block_size)
                if not buffer:
                    break
                f.write(buffer)
                downloaded += len(buffer)
                if total_size > 0:
                    percent = downloaded * 100 / total_size
                    print(f"\rDownloading... {percent:.1f}% ({downloaded//(1024*1024)}MB / {total_size//(1024*1024)}MB)", end="")
        print("\nDownloaded swapper model successfully.")
    except Exception as e:
        if os.path.exists(SWAPPER_MODEL_PATH):
            os.remove(SWAPPER_MODEL_PATH) # remove corrupted file
        raise RuntimeError(f"Failed to download swapper model from {url}. Error: {e}")

def init_models():
    global face_app, swapper
    try:
        if face_app is None:
            print("Initializing FaceAnalysis...")
            face_app = FaceAnalysis(name='buffalo_l', root=MODELS_DIR)
            face_app.prepare(ctx_id=0, det_size=(640, 640)) # Use ctx_id=0 for GPU, -1 for CPU
        
        if swapper is None:
            download_swapper_model()
            print("Initializing Swapper...")
            swapper = insightface.model_zoo.get_model(SWAPPER_MODEL_PATH, download=False, download_zip=False)
    except Exception as e:
        print(f"Error initializing models: {e}")
        raise RuntimeError(f"Model initialization failed: {e}")

@app.on_event("startup")
async def startup_event():
    # Pre-load models to avoid cold start issues
    try:
        init_models()
    except Exception as e:
        print(f"Critical Warning: Could not initialize AI models on startup. {e}")
        print("Will retry on first request. Ensure requirements are installed.")

def get_averaged_face(cv2_images: List[np.ndarray]):
    """
    Takes 4-5 images, detects the largest face in each,
    and returns a synthetic Face object blending their features for max accuracy.
    """
    faces = []
    for img in cv2_images:
        detected = face_app.get(img)
        if detected:
            # Sort by bounding box size (get the largest face)
            detected = sorted(detected, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)
            faces.append(detected[0])
            
    if not faces:
        raise ValueError("No faces detected in any of the provided images.")
        
    # If we have multiple faces, we create an averaged embedding
    # InsightFace swapper primarily uses the 'embedding' vector and 'normed_embedding'
    # We'll take the first face as a base, but average the embed vectors.
    base_face = faces[0]
    
    avg_embedding = np.mean([f.embedding for f in faces], axis=0)
    avg_normed    = np.mean([f.normed_embedding for f in faces], axis=0)
    
    # Python object dynamic property set
    base_face.embedding = avg_embedding
    base_face.normed_embedding = avg_normed
    
    return base_face

@app.post("/api/v1/generate_avatar")
async def generate_avatar(
    images: List[UploadFile] = File(...),
    template_id: str = Form("boxer_male")
):
    """
    1. Reads 4-5 images uploaded by user.
    2. Extracts 3D facial embeddings from all & averages them.
    3. Loads the 2.5D hyper-realistic template body.
    4. Swaps the seamless face onto the template.
    """
    if len(images) < 1:
        raise HTTPException(status_code=400, detail="Please upload at least 1 image (4-5 recommended).")
        
    try:
        init_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Engine initialization failed: {str(e)}")
    
    # 1. Read input images
    cv2_images = []
    for f in images:
        contents = await f.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is not None:
            cv2_images.append(img)
            
    if not cv2_images:
        raise HTTPException(status_code=400, detail="Invalid image formats uploaded.")
        
    # 2. Get the robust averaged face embedding
    try:
        source_face = get_averaged_face(cv2_images)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # 3. Load target template (body)
    template_path = os.path.join(TEMPLATES_DIR, f"{template_id}.jpg")
    if not os.path.exists(template_path):
        # Fallback empty image or raise error - in real life you'd load templates
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found on server.")
        
    target_img = cv2.imread(template_path)
    if target_img is None:
        raise HTTPException(status_code=500, detail="Failed to load template image.")
        
    # Find face in the template to swap out
    target_faces = face_app.get(target_img)
    if not target_faces:
        raise HTTPException(status_code=500, detail="No head found in the template body to replace!")
        
    # Replace the FIRST face found in the target image (assuming template has 1 character)
    target_face = target_faces[0]
    
    # 4. Perform the 3D Deep Learning Swap
    result_img = swapper.get(target_img, target_face, source_face, paste_back=True)
    
    # 5. Encode output to Base64 to send to Frontend
    _, buffer = cv2.imencode('.jpg', result_img)
    b64_img = base64.b64encode(buffer).decode('utf-8')
    
    return JSONResponse(content={
        "status": "success",
        "message": f"Successfully swapped averaged face from {len(cv2_images)} photos.",
        "avatar_data_url": f"data:image/jpeg;base64,{b64_img}",
        "template": template_id
    })

if __name__ == "__main__":
    import uvicorn
    # Run the deep learning service on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
