# AI Avatar System Architecture

## 1. Project Goal
Build a Snapchat-like AI avatar system for a game where players upload 1–3 selfies, the AI extracts facial features, and a 3D avatar face is generated and attached to a body template. Players can then customize cosmetics and generate "Style Multiverses" (different stylized versions of the same avatar).

## 2. System Architecture
- **User Selfie Upload** -> API Gateway (FastAPI)
- **Face Detection & Landmark Extraction** -> AI Service (MediaPipe, InsightFace)
- **Face Feature Vector Generation** -> Morph Targets Matcher
- **3D Avatar Face Generation** -> VRM / GLB Mapping
- **Attach Body Template** -> Pre-rigged Body Attachments
- **Avatar Customization Studio** -> Meta-data Storage (MongoDB)
- **Style Multiverse Generator** -> Stable Diffusion, InstantID, IP Adapter
- **Avatar Export** -> Game Engine (Unity/Unreal)

## 3. Technology Stack
- **Backend / AI Services**: Python, FastAPI, PyTorch, MediaPipe, InsightFace, Stable Diffusion, InstantID / IP Adapter.
- **Game Engine**: Unity (preferred for mobile/cross-platform), Unreal Engine.
- **3D Avatar Format**: VRM, GLB, FBX.
- **Database**: MongoDB.
- **Storage**: AWS S3 / Cloudflare R2.
- **DevOps**: Docker, GitHub Actions, AWS EC2 / RunPod GPU.

## 4. Components Set Up
- `/avatar_system/backend/`: Contains the FastAPI application.
- `/avatar_system/backend/main.py`: Entry point for the avatar API.
- `/avatar_system/backend/face_analyzer.py`: MediaPipe/InsightFace integration.
- `/avatar_system/backend/avatar_generator.py`: Maps face params to morph targets.
- `/avatar_system/backend/style_generator.py`: Stable Diffusion/InstantID integration.

## 5. Next Steps
1. Set up FastAPI scaffolding and required endpoints.
2. Initialize MediaPipe Face Mesh module.
3. Build the VRM morph target mapping logic.
4. Integrate Stable Diffusion / IP Adapter for the Style Multiverse.
