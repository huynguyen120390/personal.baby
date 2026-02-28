
DEFAULT_PROMPT = """You are analyzing a camera frame for child safety monitoring.

Describe the scene briefly in 3–6 short lines.

Focus on:

1) Who are present:
   - Identify baby, adult, animal, or other people if visible. How many? (e.g. "1 baby in center, 1 adult on left")
   - Approximate age category (infant/toddler/adult) only if reasonably clear.
   - Their position in the frame (left/right/center/background).
   - Tell what they are doing if clear. Anything unusual or concerning?
   - What is nanny doing? 

2) Baby safety assessment (if a baby or young child is visible):
   - Is the baby’s face clearly visible?
   - Is anything covering or very close to the mouth or nose?
   - Is the baby pressed into a soft surface?
   - Baby posture (on back / side / stomach / sitting / being held / unknown).

3) Environmental hazards:
   - Blankets, pillows, cords, small objects, toys near face,
   - Clutter or objects that could pose choking or suffocation risk.

Be cautious.
If something is unclear, say "uncertain".
Do not guess details that are not visible.
"""