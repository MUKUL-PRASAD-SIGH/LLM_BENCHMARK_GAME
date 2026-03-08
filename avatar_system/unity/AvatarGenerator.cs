using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;

/// <summary>
/// Unity integration script to interface with the AI Avatar FastAPI backend.
/// Connects the player's stored AI Face vector to VRM 3D blendshapes.
/// </summary>
public class AvatarGenerator : MonoBehaviour
{
    private string apiUrl = "http://localhost:8000/api/v1";
    
    // VRM Avatar Mesh containing BlendShapes
    public SkinnedMeshRenderer faceMesh;
    
    // Example DTO matching the FastAPI returned data
    [System.Serializable]
    public class FaceFeatures
    {
        public float jaw_width;
        public float eye_size;
        public float nose_length;
        public float lip_thickness;
        public string skin_tone;
    }

    [System.Serializable]
    public class AvatarConfig
    {
        public int user_id;
        public FaceFeatures face_vector;
        public string body_type;
        public string hair_style;
        public string outfit;
        public string active_style;
        public string new_texture_url; // Used in Style Multiverse
    }

    // Call this after successful Login/Avatar setup
    public void LoadAvatarFromServer(int userId, AvatarConfig config)
    {
        Debug.Log(">> Binding AI Avatar Parameters to 3D Mesh...");
        ApplyBlendShapes(config.face_vector);
        LoadClothing(config.outfit);
        
        if (!string.IsNullOrEmpty(config.new_texture_url))
        {
            StartCoroutine(DownloadAndApplyTexture(config.new_texture_url));
        }
    }

    private void ApplyBlendShapes(FaceFeatures features)
    {
        if (faceMesh == null) return;

        // Example mapping MediaPipe normalized outputs (0-100) to Unity VRM blendshapes
        // The blendshape indices will depend on your specific FBX/VRM rigging
        
        int jawBlendIndex = faceMesh.sharedMesh.GetBlendShapeIndex("jaw_width");
        if (jawBlendIndex != -1)
            faceMesh.SetBlendShapeWeight(jawBlendIndex, features.jaw_width * 10f); // Scaling factor
            
        int eyeBlendIndex = faceMesh.sharedMesh.GetBlendShapeIndex("eye_size");
        if (eyeBlendIndex != -1)
            faceMesh.SetBlendShapeWeight(eyeBlendIndex, features.eye_size * 5f);
            
        int noseBlendIndex = faceMesh.sharedMesh.GetBlendShapeIndex("nose_length");
        if (noseBlendIndex != -1)
            faceMesh.SetBlendShapeWeight(noseBlendIndex, features.nose_length * 20f);
            
        // Setup simple Skin Tone material tint
        Material mat = faceMesh.material;
        if (features.skin_tone == "dark") mat.color = new Color(0.3f, 0.15f, 0.1f);
        else if (features.skin_tone == "medium") mat.color = new Color(0.8f, 0.6f, 0.4f);
        else mat.color = new Color(1.0f, 0.9f, 0.8f); // Light
    }

    private void LoadClothing(string outfitId)
    {
        // Instantiates prefab bases based on outfit selection
        Debug.Log("Loading Outfit Prefab Reference: " + outfitId);
    }

    private IEnumerator DownloadAndApplyTexture(string url)
    {
        // For the Style Multiverse: Downloads the Stable Diffusion generated diffuse map
        UnityWebRequest request = UnityWebRequestTexture.GetTexture(url);
        yield return request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
        {
            Debug.LogError("Failed to download skin texture: " + request.error);
        }
        else
        {
            Texture2D tex = ((DownloadHandlerTexture)request.downloadHandler).texture;
            if (faceMesh != null)
            {
                // Assign new AI-generated style skin
                faceMesh.material.mainTexture = tex;
                Debug.Log(">> Style Multiverse Texture Applied Successfully!");
            }
        }
    }
}
