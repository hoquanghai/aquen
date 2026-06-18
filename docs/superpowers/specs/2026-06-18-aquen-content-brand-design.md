# AQUEN — Skincare Content Brand + Virtual KOL + Production Toolkit

**Design spec** · 2026-06-18 · Status: **Draft for review**

---

## 1. Overview

AQUEN is a new, AI-native **skincare content brand** for a global, English-speaking
audience. The goal of this project is to build the brand from zero and the software
"brand machine" that runs it:

1. **Grow** an engaged following in the skincare niche by attracting the kind of audience
   that already follows competitor skincare pages/accounts on TikTok, Instagram, and
   Facebook — using **only compliant tactics** (interest/lookalike targeting, viral
   content, collabs), never scraping or follower-poaching.
2. **Build the brand & produce** images and ad videos with **Higgsfield** AI tools.
3. **Research competitor viral content** and remix it into original, non-infringing videos.
4. Run everything through a **single virtual KOL ("Mira")** as the consistent face of the
   campaign.

Decisions locked with the user (2026-06-18):

| Decision | Choice |
|---|---|
| Brand name | **AQUEN** — tagline *"Hydration you can see."* |
| Market / language | **Global / English** (US, UK, SEA, AU) |
| Product reality | **Content brand first** — audience & trust first; own product later |
| Growth | **Organic viral + paid ads** (compliant) |
| Virtual KOL | **Female, East/SE-Asian, "everyday" (not photoreal)** — working name **Mira** |
| Toolkit architecture | **Python local toolkit** (CLI + lightweight local dashboard) |

> The strategy below is grounded in a 5-dimension market/competitor research pass
> (market, viral content, virtual-KOL best practice, compliant growth, naming). Key data
> points are cited inline; benchmarks from vendor/agency blogs are treated as directional.

---

## 2. Brand foundation

### 2.1 Positioning (content-first)

**AQUEN is an AI-native skincare education & curation channel** that turns barrier/hydration
science into satisfying, trustworthy, bite-size content — *"Hydration you can see."*

- **Audience:** skincare-fatigued Gen-Z & younger-millennial women (18–32), global English
  (US/UK/SEA/AU), who abandoned 10-step routines for "skinvestment" skinimalism: fewer,
  outcome-proven products; dupe-aware; distrust "anti-aging" and fear-based "clean" hype;
  visually/dopamine-driven on TikTok & IG; reward transparent ingredient education.
- **Editorial spine:** barrier resilience & hydration ("glass-skin 2.0"), explained, not
  hyped. NOT "anti-aging", NOT harsh exfoliation, NOT 10-step.
- **Why content-first works here:** it lets the virtual KOL be a credible **educator/curator**
  with no product to falsely "review", which resolves the central virtual-KOL credibility
  paradox and **sidesteps the FTC ban on AI-generated testimonials** entirely.

### 2.2 Monetization roadmap (sequenced, not now)

1. **Audience & trust** (months 0–6): grow followers + email/first-party list via an
   AI skin-analysis quiz lead magnet.
2. **Affiliate / curated partnerships** (after audience proven): recommend third-party
   products with full FTC disclosure; UGC/creator collabs.
3. **Own hero SKU** (later): a single beta-glucan + postbiotic **barrier serum** at masstige
   price (~US$24–38) — the segment with the strongest tailwinds (masstige facial skincare
   +13–14%; beta-glucan search +51% YoY; microbiome niche ~18.7% CAGR). Deferred until the
   audience de-risks the launch (Rhode / Spoiled Child playbook).

### 2.3 Visual identity (direction)

- Palette: water/light-toned, luminous, clean; soft neutrals + a single aqua accent.
- Typography: modern, soft-geometric sans; generous whitespace; "premium-relatable", not
  clinical-cold.
- Motif: light through water; dewy texture; a recurring "you can see it" reveal beat.
- Name/handle checks before hard-lock: `.com` availability, USPTO **Class 3** live-mark
  search, social handle availability. (AQUEN chosen partly for high exact-`.com` odds and
  registrability vs. crowded descriptive/-derma/-ceuticals names.)

---

## 3. Virtual KOL — "Mira"

- **Persona:** a warm, curious, slightly nerdy ~26-year-old skincare **educator/curator** —
  *"the friend who reads the studies for you."* Loves ingredient science, skeptical of hype,
  gentle and reassuring. **Always a guide, never a first-person reviewer.**
- **Appearance:** deliberately **stylized, NOT hyper-photoreal** (to dodge the uncanny valley
  and "fake flawless skin" criticism that is fatal in skincare). Relatable East/SE-Asian
  features; one signature recognizable cue (e.g. warm-brown blunt bob); healthy dewy skin
  with **real texture + curated minor "flaws"** (light freckles, slight pores). Global,
  no overt K/J-beauty cliché.
- **Voice/tone:** conversational, warm, plain-language English ("your skin barrier is
  like…"); confident but humble, anti-hype, lightly playful; explicit CTAs for comments/saves.
- **Backstory:** openly an **AI-native digital educator** — disclosed as virtual/AI on the
  bio and persistently on-content (honesty as a trust signal). "Built to read every
  ingredient study so you don't have to." No lived-experience claims, no activism, no
  illness/relationship storylines (the Lil Miquela trap).
- **Hard guardrails (DO):** self-identify as AI; educate & curate; pair with **real human
  hands** (hands-only UGC demos) and real dermatologist/creator co-signs for the efficacy
  layer; keep production quality high.
- **Hard guardrails (DON'T):** never give testimonials / before-after "results"; never claim
  human lived experience or take social/political stances; never be rendered impossibly
  flawless; never imply she is a real human; never market to under-13s.

---

## 4. Content & growth strategy

### 4.1 Content pillars

1. **Derma Decode** (save engine): one-ingredient-per-video explainers <60s (beta-glucan,
   postbiotics, niacinamide, ceramides) framing barrier resilience as "glass-skin 2.0".
2. **Texture & ASMR** (thumb-stopping hook): satisfying dewy/whipped textures, serum drops,
   hands-only back-of-hand absorption demos with sound design.
3. **Myth-Busting & Skin Truths** (comment/reach engine): debunk "irritation = proof",
   anti-aging language, harsh exfoliation, fear-based "clean".
4. **Routine & Layering** (skinimalism GRWM): streamlined 3–4-step glass-skin layering.
5. **Proof & Transparency** (trust): clinical-data callouts, lab storytelling, dermatologist
   & real-human co-signs, AI skin-analysis explainers. (No fabricated before/afters.)

### 4.2 Top viral formats to remix (originally, non-infringing)

- **Faceless hands-only texture/absorption demo** (house format) — pairs perfectly with a
  virtual KOL; real human hands carry the "usable product" realism the avatar can't.
- **Derma-decode ingredient explainer** (<60s, one ingredient) — lifts save rate ~25%.
- **Myth-busting / comment-bait debunk** — conflict + comment-gated CTA → early comment
  velocity (strongest viral signal).
- **Time-stamped before/after** — highest share rate, **but only with real human/UGC
  subjects**, never AI/avatar results (FTC-prohibited).
- **Structured listicle** (completion-incentive) — maximizes watch-time/retention.

### 4.3 Anti-plagiarism "remix" SOP (research → original)

Competitor virality is **inspiration for structure**, never a copy. For every remix:
1. Capture only the **transferable pattern** (hook archetype, beat map, pacing, format),
   not the footage, script, audio, or specific creative.
2. Re-derive an **original script** in Mira's voice + original AQUEN visuals/voiceover via
   Higgsfield; use only licensed/cleared sounds.
3. Run an **originality check** (no copied phrasing/footage; transformed substantially).
4. Log the source-of-inspiration link + the originality sign-off in the content DB.

### 4.4 Growth (compliant)

**Organic:** three-lane calendar 3–5×/week (reach/Duet · save/Derma-Decode · share/UGC);
tested 3-second hook archetypes; Duet/Stitch creators 10–100× our size; 3–8 hashtags
(never >8); single idea per 21–34s clip; ride trending audio within its 3–7-day window;
IG Collab posts + non-competitor brand/dermatologist collabs.

**Paid:** Meta **Advantage+** as primary, fed with **first-party seeds** (customer/quiz list,
video viewers 1–365d, Page/IG engagers, lead-forms); competitor-category **interest topic-
stacks** as suggestions; capture-funnel retargeting; **TikTok Spark Ads** behind proven
organic winners (own posts, or creator posts **only with their post-authorization code**).
**Never** upload/target a competitor's follower list.

### 4.5 Compliance guardrails (hard design constraints)

These are enforced by the toolkit's review gate; a post cannot be marked "ready" until all
pass:
- **FTC dual disclosure** on every sponsored/branded post: (1) commercial relationship AND
  (2) a separate **"AI-generated / created with AI"** disclosure. `#ad` alone and platform
  "Made with AI" labels are each insufficient (penalty up to ~$53k/post; dedicated FTC AI
  unit active since Jan 2026).
- **No AI-generated testimonials / before-after / fabricated efficacy** — flatly prohibited
  regardless of disclosure. Mira must never say "this cleared/improved my skin."
- **EU AI Act Art. 50** (Aug 2026) + **NY synthetic-performer law** (Jun 2026): persistent,
  repeated, plain-language on-content AI labels.
- **No** buying followers/likes/views, **no** scraping competitor lists, **no** bots /
  mass-DM / engagement pods. Spark Ads require genuine creator authorization codes.
- Substantiate all skincare claims; avoid "anti-aging" and fear-based "clean"; never market
  to under-13s.

---

## 5. System architecture — Python local toolkit

A single-developer, **Windows-friendly Python toolkit** that makes Higgsfield the creative
core and wraps it in a lightweight content-ops layer. **No SaaS lock-in. No auto-posting to
TikTok** (API-restricted); a human-in-the-loop publisher exports a ready-to-post pack.

```
                 ┌─────────────────────────── aquen CLI (Typer) ───────────────────────────┐
                 │  research · ideate · generate · screen · schedule · review · publish     │
                 └───────────────┬──────────────────────────────────────────────┬──────────┘
                                 │                                               │
        ┌────────────────────────▼───────────────┐              ┌────────────────▼───────────────┐
        │ Local dashboard (FastAPI + HTMX/Jinja)  │◄────────────►│        SQLite content DB        │
        │ board · calendar · review/compliance UI │              │ (SQLModel/SQLAlchemy)           │
        └────────────────────────┬───────────────┘              └────────────────┬───────────────┘
                                 │                                               │
   ┌─────────────┬───────────────┼───────────────┬──────────────────┬───────────┴───────┐
   ▼             ▼               ▼               ▼                  ▼                   ▼
┌────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐   ┌──────────────┐
│Research│  │ Ideation │  │  Higgsfield  │  │  Virality    │  │ Compliance  │   │  Publisher   │
│(Ad Lib │  │ + Prompt │  │  adapter     │  │  pre-screen  │  │  gate       │   │  (export pack│
│+trends)│  │ library  │  │ img/vid/audio│  │  gate        │  │  checklist  │   │  + Meta Ads) │
└────────┘  └──────────┘  └──────────────┘  └──────────────┘  └─────────────┘   └──────────────┘
```

### 5.1 Tech stack

- **Python 3.11+**, packaged with `pyproject.toml` (uv or pip).
- **CLI:** Typer. **Dashboard:** FastAPI + Jinja/HTMX + Tailwind (thin internal UI).
- **DB:** SQLite via SQLModel; Alembic for migrations.
- **Config/secrets:** `.env` (pydantic-settings); never commit keys.
- **HTTP:** httpx; retries/backoff for long-running gen jobs.
- **Testing:** pytest; adapters mocked so the toolkit is testable without live APIs.
- **External adapters (swappable interfaces):**
  - `HiggsfieldClient` — image/video/audio generation, character consistency, virality
    predictor. (API/auth details verified at implementation time; MCP fallback documented.)
  - `MetaAdLibraryClient` — official Ad Library search for competitor live ads.
  - `MetaAdsClient` — Advantage+ campaigns, custom-audience seeds, Spark Ads.
  - `TrendClient` — trending sounds/hashtags (official/public sources only).

### 5.2 Modules

1. **Research module** — query Meta Ad Library for competitor ads; capture **public** trend
   & hashtag signals; structured "manual comment-mining" notes; output **hook ideas** into
   the DB. Seeded by a **user-provided competitor watch-list** now, with an **auto-discovery**
   mode (find skincare competitors via Ad Library + trends) designed in for later. *No
   scraping of follower/customer lists, no bots.*
2. **Ideation + Prompt library** — turn hooks into scripted content ideas tagged by pillar &
   hook archetype; a versioned library of Higgsfield prompts (avatar, hands-only, texture,
   GRWM, explainer, voiceover) for repeatable, on-brand generation.
3. **Higgsfield Creative Engine** — generate the locked-consistency Mira avatar and all clip
   types + voiceover; poll jobs; pull renders into the asset store; record cost/credits.
4. **Virality Pre-Screen Gate** — run Higgsfield's virality predictor + the 6-hook checklist
   on each draft; only drafts above threshold (and opening with a tested 3-sec hook) proceed;
   scores logged back to learn what works.
5. **Content DB + Calendar** — single source of truth: 3-lane calendar, hook tags, posting
   windows (12–2pm / 7–9pm), trending-audio shelf-life timers, asset links, per-post
   compliance checklist state.
6. **Compliance Gate** — blocks "ready" until dual FTC disclosure + persistent AI label +
   claim-substantiation + no-prohibited-claim checks all pass; bakes disclosures into the
   exported caption + on-content overlay instructions.
7. **Meta Ads module** — maintain first-party Custom Audience seeds; build competitor-category
   interest topic-stacks; capture-funnel retargeting; Spark Ads with authorization codes.
8. **Human-in-the-Loop Publisher** — render queue → human review (compliance + quality +
   virality score) → **export a post pack** (video + disclosed caption + hashtags + overlay
   notes) for **manual** TikTok upload; scheduled-assist on Meta/IG where permitted.
9. **AI Skin-Analysis Hook** (later, GĐ2/3) — an on-site quiz that doubles as first-party
   lead capture feeding Meta seeds.

### 5.3 Data model (initial)

`competitors`, `ad_insights`, `trends`, `hooks` (swipe file), `content_ideas`,
`content_items` (drafts → states), `assets`, `prompts`, `calendar_slots`,
`compliance_checks`, `kol_profile`. Content item state machine:
`idea → scripted → generating → rendered → screened → review → ready → published → measured`.

---

## 6. Phased plan & first vertical slice

- **GĐ1 — Foundation:** lock AQUEN identity (name checks, visual tokens, voice guide) + lock
  Mira persona + write the anti-plagiarism remix SOP + content playbook.
- **GĐ2 — Toolkit (MVP first):** Research + Higgsfield Engine + Prompt library + Content DB +
  Compliance gate + Publisher; CLI first, thin dashboard second.
- **GĐ3 — Sample production:** build the consistent Mira avatar + a reveal image set + **3
  sample videos** (1 Derma-Decode, 1 hands-only ASMR, 1 myth-bust) with voiceover, each
  passed through the virality + compliance gates, for the user to approve quality.

**First vertical slice** (the first implementation cycle) cuts through all three: lock the
brand + Mira → stand up the toolkit MVP (Research → Ideation → Higgsfield Engine → Virality
gate → Compliance gate → Publisher export, on SQLite) → produce the Mira avatar + 3 sample
videos end-to-end. Each phase gets its own plan via the writing-plans skill.

**Scope of the first plan (locked with user 2026-06-18):**
- **In:** brand/Mira foundation, the toolkit MVP modules above, **organic** content
  production, **CLI-first** interface, research module **seeded by a user-provided
  competitor watch-list** (auto-discovery designed-in but deferred).
- **Out (later cycles):** the **Meta Ads / paid module** (organic + toolkit first), the
  **web dashboard** (CLI first, web second), the AI skin-analysis quiz, and the own-SKU
  launch.

---

## 7. KPIs

- Hook 3-sec hold rate, avg watch time / completion rate (21–34s clips).
- **Comment-to-like ratio** + early comment velocity (first 60 min) — primary, over raw views.
- Save rate on Derma-Decode; share rate on UGC before/after.
- Follower growth & reach-per-post by lane (reach/save/share).
- Paid: CPM, CTR, CVR; Spark vs in-feed; blended CAC vs LTV.
- AI skin-analysis completion → first-party list growth → conversion.
- Virality-predictor score ↔ actual performance correlation; % posts passing the gate.
- **Compliance health:** 100% of sponsored posts carry dual FTC disclosure + persistent AI
  label; zero prohibited-claim incidents; zero platform strikes.

---

## 8. Risks & mitigations

- **FTC dual-disclosure / prohibited-testimonial** → compliance gate blocks non-compliant
  posts; Mira is educator-only; before/afters are real-UGC-only.
- **Virtual-KOL credibility deficit** → content-first educator framing + real human hands +
  dermatologist co-signs + high production quality.
- **Uncanny valley / "fake flawless skin"** → deliberate stylization + curated realistic
  texture.
- **Representation landmine (Shudu pattern)** → respectful framing, real human collaborators,
  no tokenism.
- **Platform-compliance overreach** → strictly official APIs + manual research; TikTok
  publishing human-in-the-loop; no scraping/bots/bought engagement.
- **Trend/ingredient commoditization** → anchor on durable barrier/microbiome science, not a
  single viral ingredient.
- **Directional-data risk** → treat vendor benchmarks as directional; validate against the
  brand's own analytics before scaling spend.

---

## 9. Assumptions & resolved decisions

**Assumptions (verified at implementation time):**
- **A1:** Higgsfield exposes the needed capabilities (character consistency, image/video/
  audio gen, virality predictor) via API/MCP usable from a local Python process; exact auth
  & endpoints verified at implementation time, with an MCP fallback.
- **A2:** Meta Ad Library API access (token) is available for competitor ad research;
  otherwise the research module degrades to assisted-manual capture.

**Resolved with user (2026-06-18):**
- **Paid / Meta Ads module → deferred.** First cycle is organic + toolkit + production.
- **Interface → CLI first, web dashboard later.**
- **Competitor watch-list → user provides a seed list now; auto-discovery designed-in,
  deferred.** (User to paste competitor pages/handles when ready — non-blocking for planning.)
- **Geography → global English (US/UK/SEA/AU), no exclusions specified.**
```
