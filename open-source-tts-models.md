# Open-Source TTS Models for ClearGlass AI Agents (2026)

Top models with strong zero-shot voice cloning for custom personas (e.g. Aria British female voice).

## Comparison

| Model       | License    | Cloning (clean audio) | Strengths                          | VRAM    |
|-------------|------------|-----------------------|------------------------------------|---------|
| Chatterbox (Resemble) | MIT | 5-10s | Beats ElevenLabs in tests; emotion control; production-ready | ~6GB   |
| Qwen3-TTS (Alibaba)  | Apache 2.0 | ~3s | Permissive commercial; low WER; voice design | Moderate |
| Fish Speech S2      | Research (paid comm.) | Short | Highest quality/WER; 80+ languages; cross-lingual | 12GB+  |

## Usage for Custom Voice (Aria)
1. Record 5-10s clean British RP female reference audio (no noise, consistent tone).
2. Self-host via Hugging Face or GitHub (Chatterbox recommended for MIT + ease).
3. Clone and control emotion/pacing for refined advisor persona.
4. Integrate with existing AI agents (COO bot, etc.) via API/local inference.

Clean reference audio critical for accent fidelity. Supports 17+ languages including UK English.

*Added for AI automation and voice capabilities in ClearGlass ecosystem.*