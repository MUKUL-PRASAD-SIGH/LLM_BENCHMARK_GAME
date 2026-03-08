# Feature: Custom Model Avatar Selection

## Overview
Added the ability to specify an Avatar (Skin ID) when adding a Custom LLM from the `select.html` screen.

## Changes Made
- Modified `select.html` Custom Model modal form to include a `<select>` dropdown with 4 static Avatar choices:
  - Avatar 1 (Boxer)
  - Avatar 2 (Ninja)
  - Avatar 3 (Robot)
  - Avatar 4 (Brawler)
- Integrated the selected `skin_id` into the state payload sent to the backend.
- Updated `backend/server.py` `add_custom_model` endpoint to assign the requested `skin_id` dynamically instead of defaulting to `"4"`.
