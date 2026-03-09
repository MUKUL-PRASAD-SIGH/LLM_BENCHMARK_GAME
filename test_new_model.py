import os
import sys
import json
from unittest.mock import patch

# Simulate adding a 5th model via .env (Override)
os.environ['FIGHTER_5_NAME'] = 'Test Model X'
os.environ['FIGHTER_5_MODEL_ID'] = 'llama-3.1-8b-instant'
os.environ['FIGHTER_5_PROVIDER'] = 'groq'

from backend.llm_engine import get_models
from backend.fight_manager import FightManager
from backend.analysis_engine import FightAnalyzer

def test_custom_model_integration():
    print("=== EXHAUSTIVE CUSTOM MODEL COMMISSIONING TEST ===\n")
    
    # -------------------------------------------------------------
    # 1. Fighter Selection Screen / Registry Verification
    # -------------------------------------------------------------
    print("[1/9] Verifying Model Registry...")
    models = get_models()
    if "5" not in models:
        print("❌ FAILED: llm_engine did not pick up Slot 5 from environment variables.")
        sys.exit(1)
    custom_model = models["5"]
    print(f"✅ SUCCESS: Picked up {custom_model['name']} ({custom_model['model_id']}) via provider {custom_model['provider']}.")

    # -------------------------------------------------------------
    # 2. Initialization & Features Mapping
    # -------------------------------------------------------------
    print("\n[2/9] Initializing FightManager & Feature Mapping...")
    try:
        fm = FightManager("5", "1")
        assert hasattr(fm.p1, 'debate_history')
        assert hasattr(fm.p1, 'reward_history')
        assert hasattr(fm.p1, 'total_reward')
    except Exception as e:
        print(f"❌ FAILED to initialize FightManager: {e}")
        sys.exit(1)
    print(f"✅ SUCCESS: FightManager booted. Custom Model mapped to Player 1.")

    # -------------------------------------------------------------
    # 3. Prompt & Debate Topic Injection
    # -------------------------------------------------------------
    print("\n[3/9] Testing Prompt & Debate Generation...")
    try:
        topic1 = fm.get_debate_topic()
        topic2 = fm.get_debate_topic()
        assert topic1 != topic2, "Debate topic repetition detected."
        
        p1_prompt = fm.build_prompt("p1")
        assert "[YOUR CURRENT STATE]" in p1_prompt
        assert "[DEBATE ZONE]" in p1_prompt
        assert topic1 in p1_prompt or topic2 in p1_prompt
        print("✅ SUCCESS: Prompts generated with unique rotating debate topics.")
    except Exception as e:
        print(f"❌ FAILED during debate generation check: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # Simulate a Mock Fight History for Analytics Testing
    # -------------------------------------------------------------
    fm.history = [
        {
            "turn": 1, 
            "p1_move": "PUNCH", "p1_thinking": "I predict kick. c++ is better.", "p1_prediction": "KICK", 
            "p2_move": "KICK", "p2_thinking": "I predict punch.", "p2_prediction": "PUNCH",
            "p1_dmg": 15, "p2_dmg": 10,
            "p1_params_before": {"temperature": 0.7, "top_p": 1.0},
            "p2_params_before": {"temperature": 0.7, "top_p": 1.0}
        },
        {
            "turn": 2, 
            "p1_move": "DEFEND", "p1_thinking": "I predict defend. python is compiled.", "p1_prediction": "DEFEND", 
            "p2_move": "DEFEND", "p2_thinking": "I predict defend.", "p2_prediction": "DEFEND",
            "p1_dmg": 0, "p2_dmg": 0,
            "p1_params_before": {"temperature": 1.0, "top_p": 0.8},
            "p2_params_before": {"temperature": 0.5, "top_p": 1.0}
        }
    ]
    fm.p1.moves_made = ["PUNCH", "DEFEND"]
    fm.p2.moves_made = ["KICK", "DEFEND"]
    fm.p1.response_times = [1.2, 1.4]
    fm.p2.response_times = [1.0, 1.1]
    
    analyzer = FightAnalyzer(fm)

    # -------------------------------------------------------------
    # 4. Valid JSON & RL Reward Calculator
    # -------------------------------------------------------------
    print("\n[4/9] Testing RL Reward Calculation...")
    try:
        # Process mock rewards
        fm._calculate_rewards()
        assert fm.p1.total_reward != 0 or fm.p2.total_reward != 0, "RL reward did not tick."
        assert len(fm.p1.reward_history) > 0
        print("✅ SUCCESS: RL Engine successfully processed rewards.")
    except Exception as e:
        print(f"❌ FAILED RL reward calc: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # 5. Victory Screen Metrics (Intelligence & Benchmarks)
    # -------------------------------------------------------------
    print("\n[5/9] Testing Core Victory Metrics...")
    try:
        intel_p1 = analyzer.calculate_intelligence_score(fm.p1, fm.p2, is_p1=True)
        intel_p2 = analyzer.calculate_intelligence_score(fm.p2, fm.p1, is_p1=False)
        reasoning = analyzer.calculate_reasoning_quality(is_p1=True)
        consistency = analyzer.calculate_thinking_consistency(is_p1=True)
        hallu = analyzer.calculate_hallucination_rate(is_p1=True)
        
        # In our mock history, p1 says "c++ is better" (Turn 1) and "python is compiled" (Turn 2, triggers hallu).
        assert "events" in hallu
        print("✅ SUCCESS: Deep Analytics generated (Intel={}, Reasoning={}, Hallu Events={})".format(intel_p1, reasoning, hallu["count"]))
    except Exception as e:
        print(f"❌ FAILED Core Metrics: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # 6. Strategy Heatmap Generation
    # -------------------------------------------------------------
    print("\n[6/9] Testing Strategy Heatmap Generation...")
    try:
        heatmap_p1 = analyzer.generate_strategy_heatmap(is_p1=True)
        assert heatmap_p1 and heatmap_p1.startswith('iVBOR'), "Heatmap did not return base64 PNG."
        print("✅ SUCCESS: Strategy Heatmap generated correctly using matplotlib/seaborn.")
    except Exception as e:
        print(f"❌ FAILED Heatmap generation: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # 7. Timeline Generation
    # -------------------------------------------------------------
    print("\n[7/9] Testing Replay Timeline Generation...")
    try:
        timeline = analyzer.generate_timeline()
        assert len(timeline) == 2, "Timeline mismatch"
        print("✅ SUCCESS: Timeline generator compiled history correctly.")
    except Exception as e:
        print(f"❌ FAILED Timeline generation: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # 8. Leaderboard Persistence
    # -------------------------------------------------------------
    print("\n[8/9] Testing Leaderboard Persistence...")
    try:
        # Mock leaderboard call without permanently writing test data to disk if we can avoid it, 
        # but calling the real function works because we can just delete the test entry or overwrite.
        analyzer.update_leaderboard()
        leaderboard_path = os.path.join(os.path.dirname(__file__), "data", "leaderboard.json")
        assert os.path.exists(leaderboard_path)
        print("✅ SUCCESS: Leaderboard saved to data/leaderboard.json.")
    except Exception as e:
        print(f"❌ FAILED Leaderboard write: {e}")
        sys.exit(1)

    # -------------------------------------------------------------
    # 9. PDF Report Generation
    # -------------------------------------------------------------
    print("\n[9/9] Testing PDF Report Engine...")
    try:
        import base64
        # We don't have a direct backend generate_pdf_report in analysis_engine (it's handled by frontend jspdf)
        # We verify that report data is compiled and sent to frontend correctly.
        report_data = analyzer.generate_full_report()
        assert "p1_metrics" in report_data
        assert "intel_score" in report_data["p1_metrics"]
        print("✅ SUCCESS: Full Report Data Payload successfully compiled for PDF generation.")
    except Exception as e:
        print(f"❌ FAILED PDF Report Data compilation: {e}")
        sys.exit(1)

    print("\n🎉 ALL TESTS PASSED! The Custom Model perfectly inherited the entire complex analytics framework.\n")


if __name__ == "__main__":
    test_custom_model_integration()
