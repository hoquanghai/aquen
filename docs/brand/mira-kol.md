# Mira — Canonical Virtual KOL (trained Soul)

**This is the official AQUEN KOL identity.** It supersedes the exploratory concepts in
`mira-face-concepts.md`. Mira's face = the user's pre-existing consistent character (a
Vietnamese woman) generated on 2026-06-03; we trained a reusable Higgsfield **Soul** from it.

## Trained Soul
- **Name:** Mira
- **soul_id:** `83c0591d-223f-461d-b4f2-0040fa029b8b`
- **type / model:** `soul_2` (Higgsfield Soul V2)
- **Status:** training started 2026-06-18 (~10 min; queued → ready)
- **Trained from:** 10 face/portrait images from the user's 2026-06-03 batch (43 available,
  all "keep exact face/identity"). Source generation IDs used:
  `d8de3728, eebd3dc9, db052fd9, 8be654c2, 4393f2d3, 9c8c90fa` (gpt_image_2 portraits) +
  `ccb03c99, 591955c5, 4704ced9, 9c5c22e1` (imagegen_2_0). 33 more June-3 images remain for
  a future re-train with a hand-curated set if desired.

## How to use
- Generate with `generate_image` `model: "soul_2"` + this `soul_id` (or `soul_cinema_studio`
  for cinematic). The Soul is usable ONLY with `soul_2` / `soul_cinema_studio`; for other
  models use `show_reference_elements`. **One soul_id per generation** (multi-character shots
  need Elements).
- Check status: `show_characters(action="status", soul_id="83c0591d-...")`.

## Brand alignment & guardrails
- Render Mira in AQUEN skincare-educator contexts: clean aqua/white palette, dewy skin with
  REAL texture (pores, light freckles), warm/approachable, educator settings — keep identity
  consistent via the Soul.
- Mira is an **AI character — disclose as AI** (bio + persistent on-content), **educator/
  curator only, never first-person testimonials / before-after results** (FTC). See the design
  spec §3 and §4.5.
