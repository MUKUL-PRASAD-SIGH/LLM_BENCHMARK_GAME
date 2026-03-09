# Avatar System Overview

This document provides a comprehensive overview of the currently built Avatar System components, detailing the architecture, capabilities, and existing code implementations based on references and core engine logic.

## 1. Core Architecture
The Avatar System is designed to create photorealistic and stylized 3D avatars from user-uploaded images. As defined in `ai_avatar_system_architecture.md`, the pipeline follows:
1. **User Selfie Upload** via APIs.
2. **Face Detection & Landmark Extraction**.
3. **Face Feature Vector Generation**.
4. **3D Avatar Face Generation** & Template Attachment.
5. **Avatar Customization & Style Multiverse Generation**.

## 2. Deep Learning Face Swap Engine (Path 1)
Located in `avatar_system/backend/engine.py`, this microservice provides a 2.5D deep learning-based hyper-realistic avatar generation capability.

- **Technology Stack**: FastAPI, InsightFace (`buffalo_l` model), ONNX (`inswapper_128.onnx`), and OpenCV.
- **Endpoint**: `POST /api/v1/generate_avatar`
- **Workflow**:
    1. Receives 1 to 5 uploaded user images and a target `template_id` (e.g., `boxer_male`).
    2. Utilizes `insightface` to extract robust 512-dimensional facial embeddings.
    3. Computes the **Averaged Face Embedding** to eliminate noise and inconsistencies from a single photo (detailed in `get_averaged_face`).
    4. Swaps this averaged face seamlessly onto the requested archetype template body using the `inswapper_128.onnx` model, automatically matching lighting and skin tone.
    5. Returns the resulting avatar as a Base64 encoded JPEG in a JSON response for immediate frontend integration via `arena-ai.js`.

## 3. Facial Feature Extractor (Landmark Analysis)
Located in `avatar_system/backend/face_analyzer.py`, this component utilizes **MediaPipe Face Mesh** to extract precise facial landmarks.

- **Class**: `FaceAnalyzer`
- **Functionality**:
    - Generates 468+ facial landmarks from an uploaded image byte-stream.
    - Calculates derived VRM morph target blendshape scalars (normalized 0-1 metrics):
      - `jaw_width`
      - `eye_size`
      - `nose_length`
      - `lip_thickness`
    - Identifies a basic `skin_tone` by sampling an average pixel patch near the cheek.

## 4. Main Config and Style Multiverse APIS
Located in `avatar_system/backend/main.py` and `style_generator.py`, the system extends the generated avatar with advanced stylization and persistent customizations.

- **Avatar Configuration Management** (`main.py`):
    - `POST /api/v1/extract_features`: Serves a wrapper around `FaceAnalyzer`.
    - `POST /api/v1/generate_avatar` (Mock DB Version): Binds mapped facial features to base bodies (e.g., `athletic`) and applies attributes like hair color and accessories.
- **Style Multiverse** (`style_generator.py`):
    - `POST /api/v1/style_multiverse/{user_id}/{style}`
    - Allows a user's avatar to be dynamically re-rendered in different aesthetic modes (e.g., `cyberpunk`, `anime`, `warrior`, `cartoon`, `sci_fi_soldier`, `realistic`).
    - Integrated with mock Stable Diffusion + IP-Adapter/ControlNet backend setups, ready for cluster execution. It currently formulates robust SD prompts with ControlNet payload definitions.

## Conclusion
The backend deep learning component for the Avatar module is structurally complete with robust averaging logic to generate error-free hyper-realistic fighter heads. The next primary action item revolves around modifying the frontend (`select.html`) to support multi-file uploads and pipelining the Base64 responses seamlessly into the arena rendering system.
