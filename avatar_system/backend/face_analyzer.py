import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh

class FaceAnalyzer:
    def __init__(self):
        self.face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

    def analyze_face(self, image_bytes: bytes) -> dict:
        """
        Takes raw image bytes, decodes, and uses MediaPipe to extract facial landmarks.
        Returns a dictionary of normalized facial parameters for the 3D Avatar morph targets.
        """
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image"}

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(img_rgb)

        if not results.multi_face_landmarks:
            return {"error": "No face detected"}

        landmarks = results.multi_face_landmarks[0].landmark
        
        # Calculate derived metrics (distances normalized 0-1)
        # Using simple heuristic indices for MediaPipe
        # Jaw width: distance between left and right jaw outline
        jaw_width = self._calc_distance(landmarks[234], landmarks[454])
        
        # Eye size: simplified distance between top/bottom of eye
        left_eye_h = self._calc_distance(landmarks[159], landmarks[145])
        right_eye_h = self._calc_distance(landmarks[386], landmarks[374])
        eye_size = (left_eye_h + right_eye_h) / 2.0
        
        # Nose length
        nose_length = self._calc_distance(landmarks[8], landmarks[164])
        
        # Lip thickness
        lip_thickness = self._calc_distance(landmarks[13], landmarks[14])

        # Estimate skin tone trivially using an average patch on the cheek
        skin_tone = self._estimate_skin_tone(img, landmarks[50])

        return {
            "jaw_width": round(jaw_width * 10, 2),  # Scaled for arbitrary morph target 0-1
            "eye_size": round(eye_size * 20, 2),
            "nose_length": round(nose_length * 5, 2),
            "lip_thickness": round(lip_thickness * 10, 2),
            "skin_tone": skin_tone
        }

    def _calc_distance(self, p1, p2):
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def _estimate_skin_tone(self, img, cheek_lm):
        h, w, _ = img.shape
        cx, cy = int(cheek_lm.x * w), int(cheek_lm.y * h)
        
        # Safety bounds
        cx = max(0, min(w-1, cx))
        cy = max(0, min(h-1, cy))

        # Sample 5x5 area
        patch = img[max(0, cy-5):min(h, cy+5), max(0, cx-5):min(w, cx+5)]
        avg_color = np.mean(patch, axis=(0,1))
        
        # BGR -> roughly mapping to categories
        b, g, r = avg_color
        intensity = (r + g + b) / 3

        if intensity > 200:
            return "light"
        elif intensity > 120:
            return "medium"
        else:
            return "dark"

analyzer = FaceAnalyzer()
