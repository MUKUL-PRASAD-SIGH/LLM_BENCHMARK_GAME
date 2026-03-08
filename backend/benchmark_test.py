import os
import sys

# Ensure backend imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.llm_engine import MODELS, call_model

CATEGORIES = {
    "Technical": "Explain why interfaces are useful in Go.",
    "Ethical": "Should Autonomous Vehicles be programmed to protect their passengers at all costs?",
    "Scientific": "Describe the physiological limits of human breath-holding.",
    "Business": "What is the strategic value of loss leaders in retail?",
    "Creative": "Pitch a movie about a time-traveling accountant."
}

def run_benchmark():
    print("==========================================")
    print(" LLM Fight Club - Standalone Benchmark Tool")
    print("==========================================\n")
    
    # We will just do a simple pass over all registered models in memory
    results = {}
    
    for model_id, model_info in MODELS.items():
        print(f"Testing Model: {model_info['name']} ({model_info['provider']})")
        results[model_info['name']] = {}
        
        for cat_name, prompt in CATEGORIES.items():
            print(f"  -> Category: {cat_name} ... ", end="", flush=True)
            
            # Simple baseline params
            params = {
                "temperature": 0.7,
                "top_p": 1.0,
                "max_tokens": 150,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0
            }
            
            # Simulated benchmark prompt format
            sys_prompt = f"Answer concisely but accurately. Question: {prompt}"
            
            # Make the API call
            res = call_model(model_id, sys_prompt, params)
            
            if res.get("error"):
                score = "FAIL"
                print(f"FAIL ({res['error_type']})")
            else:
                # Mock score based on response length + latency just for illustration
                # In full engine, FightAnalyzer would do this
                text = res.get("text", "")
                latency = res.get("response_time", 1.0)
                
                # Higher score for longer, more robust responses (up to a point), divided by latency penalty if very slow
                base_score = min(100, len(text.split()) / 2 + 60)
                if latency > 10:
                    base_score -= 10
                    
                score = round(base_score, 1)
                print(f"OK (Score: {score}, {latency:.2f}s)")
                
            results[model_info['name']][cat_name] = score
        print()
        
    print("==========================================")
    print(" BENCHMARK RESULTS MATRIX")
    print("==========================================")
    
    # Print the matrix table
    header = f"{'Model':<25} | {'Technical':<10} | {'Ethical':<10} | {'Scientific':<10} | {'Business':<10} | {'Creative':<10}"
    print(header)
    print("-" * len(header))
    
    for model_name, cat_scores in results.items():
        row = f"{model_name:<25} | "
        for cat in CATEGORIES.keys():
            val = str(cat_scores.get(cat, 'N/A'))
            row += f"{val:<10} | "
        print(row)
        
    print("\nBenchmark complete.")

if __name__ == "__main__":
    run_benchmark()
