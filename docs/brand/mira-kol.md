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

## Clean still-image production pipeline (IMPORTANT)
- **Do NOT use `soul_2` for finished stills.** Its "General" style reliably hallucinates a
  fake phone / Instagram UI chrome + a thumbnail filmstrip + gibberish text, and ignores
  "no text/UI" negatives. (Soul `soul_2`+soul_id is still fine for the identity reference and
  for `soul_cinema_studio` video.)
- **Use a reusable Element + Nano Banana for clean photos.** Element **`Mira-1`**
  (element_id `1972c3b9-1f3f-49fb-bcf0-104c7b171a23`, built from the clean soul render
  `c6c2ddd4`). Generate with `generate_image` `model: "nano_banana_2"` (resolves to Nano
  Banana), embedding `<<<1972c3b9-1f3f-49fb-bcf0-104c7b171a23>>>` in the prompt. Output is
  clean, photographic, single-frame, identity-faithful.
- **Prompt recipe:** describe a plain candid photo ("a clean realistic photograph of
  <<<id>>> …, one person, one frame"); AVOID trigger words "beauty-channel / short-form
  video / editorial / brand headshot"; end with "no text, no captions, no phone or app
  interface, no social-media UI, no logos, no watermark."
- First clean educator set (2026-06-18): `f8c2253d` (talking), `2ee2fc4f` (headshot),
  `e582cad1` (derma-decode point-to-cheek), `3be3c6df` (explaining, shelf bg).

## Video pipeline (image → video)
- Animate a clean still with `generate_video` `model: "minimax_hailuo"` (Hailuo 2.3, natural
  facial emotion), 9:16, 6s, `medias:[{role:"start_image", value:<image_job_id>}]` + a motion
  prompt. ~6 credits/clip. Face identity is inherited from the start still.
- First sample reel (2026-06-18, silent motion — NO voiceover/lip-sync yet):
  `fd04fe45` derma-decode talking (from `3be3c6df`), `5af8472a` myth-bust talking
  (from `f8c2253d`), `cdc50fb0` hands-only ASMR (from hands still `0cc1da9c`).
- NEXT production layer (not done yet): TTS narration + lip-sync + on-screen captions (with
  the FTC + AI disclosures) + BGM. That's the toolkit/hyperframes step, not raw Higgsfield.

## Brand alignment & guardrails
- Render Mira in AQUEN skincare-educator contexts: clean aqua/white palette, dewy skin with
  REAL texture (pores, light freckles), warm/approachable, educator settings — keep identity
  consistent via the Soul.
- Mira is an **AI character — disclose as AI** (bio + persistent on-content), **educator/
  curator only, never first-person testimonials / before-after results** (FTC). See the design
  spec §3 and §4.5.
