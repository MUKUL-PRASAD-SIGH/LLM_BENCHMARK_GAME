# Reasoning Score & Thinking Consistency

## Description
This updates the LLM benchmark's post-match analysis engine to correctly grade how well each model 'reasoned' its turn execution. Previously models were forced to produce output but not actually checked to see if they provided strong or factual reasoning.

## Added Metrics
1. **Reasoning Quality**: Inspects the length and tactical vocabulary points (like mentioning "distance", "predict", and "opponent") in the reasoning string. Good explanation earns more score.
2. **Thinking Consistency**: Inspects if the `prediction` accurately matched reality, and additionally cross-checks the text within the `thinking` object to ensure the matched prediction was explicitly identified by the model inside its string text block.

## Upgraded Analysis Score
The outputted Strategic Score metric has been updated dynamically. It takes into account the standard battle stats (HP, total damage dealt), but has been tuned down significantly to carve out strong statistical representation for the new `reasoning_quality` and `thinking_consistency` data points.
