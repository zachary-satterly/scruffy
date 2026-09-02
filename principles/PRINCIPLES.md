# PRINCIPLES — a curated list of AI design principles

**The source-of-truth corpus for the Scruffy skill.** This file is the growing, creditable, hand-tweakable layer; the skill's §C carries a compiled snapshot so it runs standalone. Edit here, then recompile §C via the skill's §I distillation pass — never patch §C directly, or the edit dies with the snapshot.

**Citations:** `[video_id t]` = a YouTube video (`youtube.com/watch?v=<id>`) at that timestamp. §1–20 distill Kole Jain's channel (50 videos). §21–22 are field-derived axes validated for compilation on 2026-08-08. §23–27 distill the completed 18-video Priority 1 pilot; §28–32 record the 16-video targeted Priority 2 pilot. New creators enter via `scripts/intake.py`, get distilled into a new numbered section here, and inform the next reconciliation of the operational skill. Principles are distilled and attributed; no source text is reproduced.

**Currently distilled:** Kole Jain (§1–20) · Steven Haney/YC Design Review (compiled directly into skill §C) · Sergei Chyrkov (§23) · DesignCourse (§24) · UI Collective (§25) · NNgroup (§26) · Deque Systems (§27) · Eleken (§28) · Kevin Powell (§29) · Tim Gabe (§30) · Baymard Institute (§31) · selected YC Design Review (§32) · Laws of UX reconciliation (§34). The researched 2026-08-08 queue, exact starter videos, scope limits, and exclusions live in `SOURCES.md`.

**Source-admission boundary:** a vetted or queued channel changes no detector rule by itself. Only transcript-distilled, timestamp-cited observations enter a numbered section. Taste-led redesign content may support visual hypotheses, but it cannot establish product, interaction, accessibility, or severity claims without research-backed or live-field corroboration.

## 1. Data drives the form (dashboards, tables, data UI)

- The UI shape should come from the data, not a generic layout. Enumerable values → chips; numbers → right-aligned so digits align by place value; long text truncated; inactive rows shaded. [Ksx9C2-3yMo 0:21]
- Time-delineated data usually wants a timeline, not a time-sorted table; charts roll up any time-dimensioned data instantly. [Ksx9C2-3yMo 1:16]
- Dashboard color comes from the data (urgent = red icon, avatars for who-did-what), never sprinkled decoration. [Ksx9C2-3yMo 1:46]
- Main dashboard area reflects what matters most to the user (PM tool → project status up top; finance → investments). [B7k5rOgmOGY 2:20]
- Top strip is for page-level actions/navigation. Homepage data stays minimal. [B7k5rOgmOGY 2:44]
- Charts: no unlabeled "weird" charts; grid lines + axis numbers (always forgotten), summary, range selector; favicons/icons for identification. [B7k5rOgmOGY 3:37]

## 2. Progressive disclosure & the spectrum of explicitness

- Hierarchy isn't only visual — it's what you show vs hide. Infrequent actions go in popovers/hover reveals, not permanent chrome. [Ksx9C2-3yMo 2:24]
- Spectrum of explicitness: global always-visible button (high) → icon-on-hover (low). Place each action deliberately on that spectrum. [Ksx9C2-3yMo 3:26]
- Onboarding = sequenced disclosure: one tooltip → next → checklist; never a six-bullet modal dumped at login. [Ksx9C2-3yMo 3:48]
- Popover = simple + non-blocking; modal = complex but same-page context (blocking, pair with confirmation toast); new page = permanent/large context (needs back button/breadcrumb). [B7k5rOgmOGY 4:40]

## 3. Invisible UI (the finished-product tell)

- UI is as much what you can't see: hover copy chips, comment indicators, tooltips, empty/error/warning states, feature announcements. Beginner dashboards almost universally lack tooltips. [Ksx9C2-3yMo 4:59]
- Every widget needs its full state set: default, hover, active/pressed, disabled (+ loading). Inputs: focus, error (border + message), warning. Every interaction gets a response. [EcbgbKtOELY 7:31]
- Empty states are designed, not accidental. [B7k5rOgmOGY 3:18]
- Optimistic UI for snappiness (act as if the server call will succeed). [B7k5rOgmOGY 7:45]

## 4. Visual hierarchy

- Contrast (big vs small, colorful vs not) IS the hierarchy. Most important: top, large, bold; secondary info smaller/greyer below. Price-type key values: top, right-aligned, accent color. [EcbgbKtOELY 0:47]
- Images/icons+lines communicate faster than words (from→to as icons + line). [EcbgbKtOELY 1:33]
- Whitespace beats grids: 12-col/8pt are guidelines; grouping related elements is hierarchy too; 4-pt system works because everything halves cleanly. [EcbgbKtOELY 2:05]

## 5. Typography

- One font, nearly always. Sans-serif, and stop spending time there. [EcbgbKtOELY 3:17]
- Large text: letter-spacing −2…−3%, line-height 110–120% → instantly professional. [EcbgbKtOELY 3:45]
- Landing pages ≤ ~6 font sizes (wide range OK); dashboards: rarely >24px, tight range, high density. [EcbgbKtOELY 4:05]

## 6. Color

- One primary (brand) color; lighten for backgrounds, darken for text; that's halfway to a color ramp. [EcbgbKtOELY 4:57]
- Semantic colors carry meaning: blue trust, red danger, yellow warning, green success — destructive buttons are red even when purple is "on brand." [EOcY3hPMQkk 5:39]
- Too many colors = competing accents + WCAG failures. Icons need no color (recognizable symbols; color = status only). [EOcY3hPMQkk 0:15]
- Neutral balance: backgrounds stay in the background (neutral gray + light foreground; tint the gray with brand hue for warmth — Headspace). Sometimes the fix is a border, not another colored layer. [EOcY3hPMQkk 1:27]
- Adapt brand colors when they fail: rotate on the wheel (analogous), take a complement, or darken to pass WCAG (Mailchimp, Airbnb do this). [EOcY3hPMQkk 2:36]
- Grays over pure black/white, driven by hierarchy; reserve white for the most important actions (esp. dark mode). [EOcY3hPMQkk 4:06]
- Dark mode ≠ inversion: lighter-than-background cards for depth (no shadows), brighter borders, light-gray text, desaturated accents/logos. [EOcY3hPMQkk 4:55, EcbgbKtOELY 5:48]
- Element states by color: hover slightly lighter, pressed slightly darker, disabled desaturated; mobile uses press-darkening instead of hover. [EOcY3hPMQkk 6:14]

## 7. Details that scream "vibe-coded" (fast tells)

- Emojis where icons belong (use Phosphor/Lucide). [PDcQJOPby1k 0:18]
- AI-picked bright clashing colors; color via buttons/icons instead of charts. [PDcQJOPby1k 0:39]
- Same KPIs repeated across pages; contextual data in the wrong nav section; gradient letter-avatars; busy cards (collapse to ⋯ menu, chips→icons). [PDcQJOPby1k 1:11]
- Cards that do nothing; five pricing plans; plan name bigger than price; hidden discounts creating nonsense ordering. [PDcQJOPby1k 3:24]
- Sparse flyouts where a modal fits; advanced options not collapsed. [PDcQJOPby1k 2:04]
- Shadows you notice first = wrong (lower opacity, raise blur; popovers > cards in strength). [EcbgbKtOELY 6:21]
- Oversized icons (match icon size to text line-height). Ghost buttons for nav; button padding: horizontal ≈ 2× vertical. [EcbgbKtOELY 6:54]
- Overlays that ruin image and text: use gradient → readable background, optionally progressive blur. [EcbgbKtOELY 8:37]

## 8. Landing pages — the four levels ladder

Grade a landing page by level, then prescribe the next level's fixes [eMMiLeo_UGI]:

- L1 (2/10, template): alternating text/image rows, stock images, flat nav, haphazard accent color, no animation, verbose vague copy.
- L2 (6/10, identity): stacked hero, real product screenshot as the color source, white buttons, matched CTA labels (one mental model), menu hierarchy + balance, simple load animations, logical flow.
- L3 (8/10, craft): curated/zoomed product visuals, vertical frame lines, bento grids, interactive multi-selects, brand elements (badges, logo walls, social proof), mega menu, smooth animations, near-seamless flow. Designer becomes product designer.
- L4 (10/10, detail): visuals crafted not zoomed; copy shifts from *what it does* to *how it helps* ("analyze data quickly" → "turn data into decisions"); color threaded expertly; blur/motion polish; mega menu morphs instead of reopening; hover-revealed CTAs; content made for the space. No 3D/custom-illustration required.
- Universal tells: sharp vs rounded corner mismatches; images carrying color the palette should carry; landing pages are presentation — graphics (even skewed product cards) beat lame icons; trust is subconscious. [PDcQJOPby1k 5:36]

## 9. Affordances & signifiers (vocabulary)

- Containers signal relation/selection; gray = inactive; good UI explains itself without instructions (press states, active nav highlights, hover states, tooltips). [EcbgbKtOELY 0:00]
- Micro-interactions confirm outcomes, not just states (copy button needs the "copied" chip). [EcbgbKtOELY 8:09]
- Reconciled identity check: a wordmark, monogram, or product abbreviation must read as identity rather than an unlabeled control. A bordered shape, hover treatment, or control-sized box around unfamiliar initials borrows button affordance without promising an action; prefer the clear name or make the brand role unmistakable. [EcbgbKtOELY 0:00][Ksx9C2-3yMo 3:26][AH_ugxmLeUM 3:34]
- Reconciled affordance-fidelity check: inspect the inverse of every control family. A non-interactive status, badge, wordmark, or panel that borrows a button's border, padding, size, casing, hover treatment, or corner language creates a false promise even when the real buttons are internally consistent. [EcbgbKtOELY 0:00][AH_ugxmLeUM 2:40–3:18]

---

## 10. Typography — the numbers

- Font count: 1 fine, 2 sweet spot (display+sans or sans+serif), 3 pushing it, 4 a defect. Display/handwritten fonts never at paragraph size ("a design sin"). [7sUUzOCv47U 3:07, 3:49]
- Kern display type: −2…−4% letter-spacing above ~70–80px; auto-kerning breaks at scale. Letter-spacing scales inversely with size. [c1TvOcKdBVE 0:22][7sUUzOCv47U 2:03]
- Type-scale ratio √1.62 ≈ 1.27 general purpose; cube root of 1.62 for dashboards/mobile (dense, closely spaced sizes). Golden ratio 1.62 only works for a single header/body pair. Prefer fluid clamp() type over breakpoints (viewport bounds 320–1920px). [7sUUzOCv47U 8:19–10:24]
- Line height ~150% body, 110–120% headings; raise as text shrinks or lines lengthen. [7sUUzOCv47U 11:46][EcbgbKtOELY 3:45]
- Weight and opacity are interchangeable hierarchy levers. Max two weights (≥1 step apart), max two text colors (100% + one at 40–70% opacity). Smallest text must NOT also be lowest contrast. You should be able to verbally rank every text element and see styling match the ranking. [7sUUzOCv47U 4:51–6:12][Lp6ey4AyDzA 0:40]
- Hero copy: ~7-word headline / ~14-word subhead is a drafting heuristic, not an audit threshold; test literal comprehension for the defined audience. Don't let sizes across the page diverge into “two different websites” — unify unjustified outliers. [9WVt1CelBfg 1:02][RynySryqM_0 3:32–3:53][V3Omp1hm0Sg 4:25]
- Giant display text as a design object: once, at most twice per page. [Lp6ey4AyDzA 4:51]
- Treat a multi-line identity or title as a composed lockup, not as ordinary browser wrapping. Inspect the actual rendered line boxes: a connector such as `&`, `and`, or `+` stranded on its own line must be deliberately scaled and optically placed relative to the names or phrases it joins. Stress short, long, compound, and localized text at real widths; preserve intentional asymmetry, but never mistake an automatic stair-step for a design decision. [field 2026-08-16]

## 11. Spacing, corners & grids — the numbers

- Proximity encodes grouping: heading→subtext 8px, eyebrow→heading 12px, buttons→text 32px. 4/8px base grid for small elements; large dimensions round to 5/10 (120 vs 128 is imperceptible). [9WVt1CelBfg 0:41][c1TvOcKdBVE 6:06]
- Nested corner radii: inner = outer − gap (30 outer, 10 gap → 20 inner). Equal nested radii is a visible tell. Pills need no correction. Mixed radii across similar components = beginner tell; standardize (e.g. 10px). Max iOS corner smoothing for premium squircles. [c1TvOcKdBVE 1:08–2:03][AH_ugxmLeUM 2:48]
- Chip padding: vertical = ¼–½ of horizontal; chips are thinner than buttons and never carry the primary CTA color. Button padding: horizontal ≈ 2× vertical. [gKM6b2EnW1k 9:12–9:33][EcbgbKtOELY 6:54]
- Overusing whitespace is also a failure: giant gaps make elements float with no hierarchy — pulling related things closer CREATES hierarchy. [V3Omp1hm0Sg 0:41]
- Section boundaries must make grouping legible. A free-standing control that touches a preceding bordered panel reads as attached, clipped, or owned by that panel; measure edge-to-edge gaps, keep them on the spacing grid, and make the break before the next major section stronger than an ordinary within-group gap. Zero-gap adjacency is valid only for an intentional joined control. [EcbgbKtOELY 2:05][V3Omp1hm0Sg 0:41]
- Design at real viewport height: 1920-wide desktop leaves ~1000px after browser chrome; Dribbble shots cheat with ~50% more. Review at true scale on the target device. [BvbFPzLjWcU 3:25][Lp6ey4AyDzA 6:26]
- Grid-breaking is fine if balanced; breaking elements should funnel attention toward the center. Users expect conventions (top-nav, L→R, obvious CTA) — deviate only in service of the user. [AH_ugxmLeUM 2:05][SfX43uIubj4 1:22][HE4rLEQpiXY 1:41]

## 12. Product-UI color systems — the numbers

- 60-30-10 does NOT apply to product UI; real products skew hard (Vercel ≈ 90/8/2). Product needs ~4 background layers, 1–2 strokes, ~3 text tones before hovers; landing pages 3–5 neutrals. [66oOi9OLMCw 0:00–0:42]
- Backgrounds near-white, rarely pure (Linear 99%, Vercel 98%) so pure-white cards can sit on them. Never pure white/black — tint with the accent hue (GitHub dark-blue, light-orange). Tailwind fallback: light = 50 bg + 500 accent; dark = 950 bg + 300 primary. [66oOi9OLMCw 0:21][c1TvOcKdBVE 6:48–6:56]
- Text tone ladder: headings ~11% white, body 15–20%, subtext 30–40%. Button darkness tracks importance (ghost → black); most utility buttons ~90–95% white. Card edges ~85% white, not thin black borders. [66oOi9OLMCw 1:22–1:43]
- Accent as a ramp: primary 500/600, hover 700, links 400/500; dark mode drops primary to 300/400. Dark mode needs DOUBLE the tonal spacing (4–6% steps vs 2%) and surfaces must lighten as they elevate; never invert light mode — collapse colors closer instead. [66oOi9OLMCw 2:25–4:08][Vy0KKvZJRH8 4:54]
- Palette math: HSB darker step = sat +20, brightness −10, hue ~20 toward blue. OKLCH chart series: fixed lightness/chroma, hue +25–30 per series for equal perceived brightness. Theme a neutral ramp: L −0.03, C +0.02, shift hue. [c1TvOcKdBVE 3:26–3:47][66oOi9OLMCw 4:50–5:53]
- Muted colors are the maturity tell: off-whites, bluish-blacks; saturated-corner-of-the-picker colors = beginner. Gradients only within one hue; if a gradient/shadow isn't clearly working, delete it. [Lp6ey4AyDzA 3:06, 5:31][6CC8lLnqa28 0:46][AH_ugxmLeUM 1:06]
- Shadow math: x ≤ y, blur = 1.3–2× y, opacity 15–20% (not Figma's 25%), light-gray not transparent-black. [Lp6ey4AyDzA 5:52][NtZeYmTMuo4 0:20]

## 13. Components: buttons, forms, nav, cards, footers

- One primary CTA per screen/section; two equally weighted filled buttons = hierarchy failure. Destructive confirm modal: destructive action gets the red fill, Cancel gets outline/reduced opacity. [Lp6ey4AyDzA 3:49–4:10][6CC8lLnqa28 2:58]
- Review every unique rendered button pattern as a component, not just the shared CSS class: its shape must fit the job, equivalent actions must share radius and proportions, horizontal padding should be about twice vertical padding, and an ordinary action must not become a banner-sized rectangle without a task reason. [AH_ugxmLeUM 2:40–3:18][EcbgbKtOELY 6:54]
- Read the words inside every button at normal scanning speed. Functional controls use a specific verb and restrained casing/tracking; widely spaced uppercase is an identity or ceremonial treatment, not the default for an operational action. Preserve deliberate compact icon controls and editorial display treatments only when their role remains unambiguous. [AH_ugxmLeUM 2:40–3:18][EcbgbKtOELY 3:45][Ksx9C2-3yMo 3:26]
- Do not grade every surface by one density or presentation ideal. Operational dashboards prioritize scan order, state comparison, and literal actions; creation flows prioritize sequence and field grouping; media galleries prioritize identity, imagery, and one contribution path; presentation screens minimize chrome. A coherent product can—and often should—use different compositions while retaining shared tokens and interaction semantics. [Yr2uIcFZDDQ 2:21–7:12][gKM6b2EnW1k 3:24–4:05][Gfsd8NNuD9g 1:32–3:30]
- In a repeated operational collection, inspect the complete row anatomy: label, value, supporting detail, state, height, and divider. Related pieces stay close; peer rows stay comparable; a three-line fact does not become a tall card merely because space is available. [V3Omp1hm0Sg 0:41][Ksx9C2-3yMo 0:21][gKM6b2EnW1k 3:24–4:05]
- Make exceptions louder than reassurance. Repeated healthy or Ready states remain quiet and aligned; Blocked, unavailable, or actionable states receive the semantic color and local emphasis. Do not make every status an equally loud uppercase badge, and do not label an unfinished rehearsal as a generic warning when “To verify” names the task more accurately. [EOcY3hPMQkk 0:15][Ksx9C2-3yMo 4:59][q1lGlhRnzsM 1:01–1:44]
- Recovery copy belongs beside the state it resolves and names the condition, actor, next action, and retained state when relevant. Delete a separate recovery card when the blocked row already explains the action; remove duration, scope, or exclusion prose when nearby headings and controls already communicate it without ambiguity. [Yr2uIcFZDDQ 5:50 adjacent][q1lGlhRnzsM 1:01–1:23][EcbgbKtOELY 4:05]
- Forms: never placeholder-as-label (label above, placeholder = example value); input fill off-white + stroke at 40% opacity; sign-up modal needs explicit "Create account" + switch-to-login link. [gKM6b2EnW1k 6:48–7:29]
- Mobile tab bar: protruding center "+" is an anti-pattern — inline it; inactive icons need real contrast; labels optional by icon obscurity; ≤5 links (3–4 ideal), targets >44px. [gKM6b2EnW1k 0:20–1:21][Gfsd8NNuD9g 0:20]
- Card grids: whole card is the link (hover arrow), no per-card CTA unless the action is specific. Image cards: image ~¾ height + genuinely smooth gradient overlay. Fewer containers/dividers/lines — whitespace separates; tight lists: alternating row tint beats per-row lines. [gKM6b2EnW1k 3:24–4:05][c1TvOcKdBVE 5:26–5:52][Lp6ey4AyDzA 1:21]
- Kill labels the UI already implies; group related fields, rank groups, right-align paired values, icons for minor details. [c1TvOcKdBVE 4:30–5:10]
- Pricing cards: checkmarks not bullets, show ≥1 feature the tier lacks, honest billing note, verb CTA, tinted band instead of divider; CTA above features must demote to outline. ≤4 plans; price bigger than plan name; show the discount and what the next tier adds. [gKM6b2EnW1k 4:46–5:26][PDcQJOPby1k 3:24]
- Footers sized to content: 3–5 links = centered logo/links/socials, not a five-column mega-footer. Hero with a functional input/search beats a plain button. [gKM6b2EnW1k 7:50][pGYLZyBE32o 1:01]
- Icons: one family, consistent stroke/fill; size = text line-height; unlabeled only for universal glyphs, else tooltips; icons need no color (color = status). [AH_ugxmLeUM 3:34][Lp6ey4AyDzA 2:04][EcbgbKtOELY 6:54]
- Carousels: position indicators + real arrows (dark blurred pill), 3–10 cards max; swipe affordances always need a button/long-press equivalent. [gKM6b2EnW1k 10:01][P2ksReDwWkE 7:35][14h1VnkQvIc 4:14]

## 14. Charts & dashboards (deep set)

- Never smooth/curve data lines (can't locate the data point); don't fade the line at the newest data; bar counts must match the data (16 bars ≠ 7 days); no rounded bar tops hiding values. [gKM6b2EnW1k 2:22][Yr2uIcFZDDQ 4:27][AH_ugxmLeUM 6:22]
- Minimum chart kit: horizontal gridlines + point markers; full-size adds vertical gridlines, visible timeframe selector, legend, expand icon; previous-period gray comparison line is high value. [gKM6b2EnW1k 2:02–3:03][Yr2uIcFZDDQ 4:48]
- Dashboard = priority grid: rank every module, most important top-left, low priority bottom-right; consolidate orphan widgets into their logical parent; delete widgets whose meaning you can't state; never show the same fact twice. [Yr2uIcFZDDQ 2:21–7:12]
- No obvious-from-context screen titles ("Financial Dashboard"); primary content is a section, not a click; duplicate controls (two search bars) are defects; alerts need a warning icon + concrete facts (amount/date/place). [Yr2uIcFZDDQ 1:01–5:50]
- Match chart type to data (two-sided bars for income/expense, pie for composition) — "data representation will make or break the dashboard." [Yr2uIcFZDDQ 6:51–7:53]

## 15. Mobile & native patterns

- Mobile type goes UP not down (iOS base 17px vs macOS 13px). One screen, one job; add pages, not layouts. Sections flow in ONE direction (stack or h-scroll, never both). Four building blocks: cards, text/links, images, inputs; no double-nested cards. [Gfsd8NNuD9g 1:32–3:30]
- Thumb reach: primary actions at the bottom; Fitts's law — enlarge target, shorten travel (TikTok: swipe target ≈ whole screen); right-side action rails for the right-handed majority. [goWOAFqJHpA 1:30][ixUq4HM4FNg 4:51–5:07]
- Bottom sheets when context must persist; background zooms out on open; long-press blurs + zooms target; contextual (not persistent) actions. Both empty states designed: first-run (point at primary action) and no-results (acknowledge query, suggest, exit). [Gfsd8NNuD9g 3:44–6:27]
- macOS-native: global actions top bar / nav sidebar / content center; top ~50px = drag region; traffic lights integrated; prominent search; drag-in AND out; shortcuts need visible feedback + cheat sheet; onboarding ends by making the user perform the shortcut. [Vy0KKvZJRH8 2:25–8:15]
- Slide-to-confirm for irreversible actions (harder to trigger accidentally). [14h1VnkQvIc 5:07]

## 16. Motion — recipes and limits

- Almost never linear easing; expo.inOut (or equivalent bezier) is the premium signature. Working values: hover pop spring 500ms/stiffness 636/damping 24; spinner spring stiffness 550/damping 40; stagger 0.2s, duration 0.6s; tooltip delay 1000ms. [14h1VnkQvIc 0:42][ld1zhQMXxXU 2:49–4:19][d4MF6pdAZNw 5:36][NtZeYmTMuo4 8:18]
- Load reveal: content beneath must move WITH the preloader (offset down, slide together); nav fades in after, ~0.3s plain. Hold ~800–1000ms, main reveal 700–1300ms. [nl8OFGdx75w 1:00–2:28][d4MF6pdAZNw 5:57]
- Five animation types to audit: entrance, hover/click, scroll, looped, mouse. Default posture subtle; break the pattern exactly once per page. Looped = slow and minimal; mouse-follow needs touch fallback; scroll-jack sparingly if ever. [ZsP20PN14O0 0:00–5:46][tNMAFjzapOk 3:19][HE4rLEQpiXY 4:07]
- Direction encodes meaning: up-from-bottom = temporary, in-from-left = flow progress. Motion must serve clarity (morph product image into next section), never exist for itself. [tNMAFjzapOk 2:11–4:47]
- Every click gets immediate feedback (gray on press, spinner if slow) and feedback propagates (fill save icon AND badge the Saved tab). Slide-in checkmarks via mask beat fade-ins; incoming elements get a few px offset + opacity 0 so they slide-fade in. [AH_ugxmLeUM 5:32–5:50][NtZeYmTMuo4 3:08–9:41]
- Heavy 3D is dated, not premium ("$30k-GPU sites"); it mainly distracts from weak design. Judge rotating 3D by lighting artifacts. Usability is the ceiling on all effects. [VPeTgU7la34 4:07][A_Ozpb0XDuw 0:49–4:10][6CC8lLnqa28 4:06]

## 17. Landing-page section library

- Logo wall = near-universal social proof (41/50 SaaS sites); premium = marquee + edge gradient + progressive blur. Competitor call-outs are a legitimate section (soft: Coda; shameless: Basecamp). [VPeTgU7la34 0:21–1:43]
- Default hero (big headline + big product image + space) works but must be differentiated by ONE thing: distinct font, inline diagram, or interactivity. Giant-headline hero: contrast between ~290px display and tiny nav, navbar placed BELOW the headline. [VPeTgU7la34 2:03][P2ksReDwWkE 3:05]
- Tabbed multi-section: design EVERY tab (shipping one is the tell). Bento: needs enough content; don't lock the grid before the content plan; keep it dev-implementable. Scroll-stacked cards fit 3–5 steps. [VPeTgU7la34 3:25–5:49][P2ksReDwWkE 6:12–8:57]
- Images in nav dropdowns = highest-value modern pattern (menu-with-photos effect; Rivian R1T vs R1S). [VPeTgU7la34 6:30][EHwZzWd-OnQ 7:37]
- Section variety is required: two consecutive sections with identical structure = flag; flip one, or convert to bento/slider. Break-the-box overlaps beat everything-in-frame layouts. Text-only sections need 3+ lines or the whitespace reads empty. [V3Omp1hm0Sg 4:46–6:49][ulSOdTgoGeY 0:41–2:55][P2ksReDwWkE 11:21]
- Image treatments that always work: background-removed cutouts, tight detail crops, wide shot + scrim + text; mask images into the site's shape language; sample section background gradients from adjacent images; text over photos ALWAYS needs a scrim and must avoid the focal point. [ulSOdTgoGeY 2:24–2:45][V3Omp1hm0Sg 2:44–5:06]
- Underused trends: hand-drawn overlays on clean type (low skill, high payoff); structural line grids (Vercel); text-swap on scroll; animated process diagrams; 404 pages as free personality. [EHwZzWd-OnQ 1:17–7:17][SfX43uIubj4 5:55]

## 18. AI-product UI patterns

- Prompt box above the fold is the expected AI pattern; good ones preview attachments, collapse pasted code, offer mode chips + context attach + advanced-mode disclosure. [If7iCPDy2vk 0:21–0:42]
- Stream word-by-word into skeleton/shimmer placeholders; short looping fluid loaders (Notion dots, Claude star). Show the work (research-trail steps fading in) — collaborator, not black box. Confidence pills (high/unverified, click for score). [If7iCPDy2vk 1:23–5:10]
- History judged on retrievability (previews, delete, search); memory exposed and user-controllable; inline prompting (highlight → type) beats regeneration. [If7iCPDy2vk 1:51–2:48]

## 19. Vibe-code tells (expanded)

- The big three AI fixes: fonts, alignment, color. Emojis-as-icons = #1 generated-UI signature. Purples too purple, backgrounds too blue-gray, low-contrast chips; semantic color misuse (everything in "completed" green; "in progress" with no %). [xHD01_Onac0 3:07–5:32]
- Structural symptoms: useless nav section labels ("Menu", "Other"), misaligned sidebar items, gradient letter-avatars, stray account rows, cards that do nothing, flat empty density (AI drops dense detail silently). [xHD01_Onac0 4:55][PDcQJOPby1k 1:11–3:24]
- "Corporate AI mush" fix: context-carrying decoration (product-relevant illustrations, scribbles) with generous text spacing; friendly plain copy over jargon (Basecamp). [SfX43uIubj4 0:00–5:10]
- Dribbble-not-shippable markers: no logo, decorative blobs, testimonial-in-hero, notched cutout images, absurd copy, oversized canvas. Aesthetic-usability effect cuts both ways — pretty is perceived as usable, so verify function separately. [BvbFPzLjWcU 0:00–2:45][5JxUJ1fuyO8 7:13]

## 20. Engagement mechanics & dark-pattern flags

- Gamification kit: central earned currency + second purchasable currency, visible progress (done AND remaining), social layer with promotion/demotion bands, rewards tied to real goals, completion hunts. Onboarding: connect data → reassure on privacy → show value BEFORE asking for goals. [jSxxAFxjxbU 0:25–4:47]
- Personalization must be legible (recognizable buckets, shareable representations) — hyper-specific AI categories failed in Spotify Wrapped; comparison-to-past-self framing is cheap high value; never remove features users anchored on. [goWOAFqJHpA 0:00–5:27]
- Flag as dark patterns: shame-nag modals with subscribe-to-dismiss, ad-gated continues, blocking housekeeping modals with no off-ramp, demoralizing goal framing, streak-punishment games, walls on trivially expected content, social-pressure checkout add-ons. [BUDipdbKK7Y 0:34–4:17]

## 21. Editorial slop — validated field axis

**Admission:** the field candidates were checked against the standing corpus plus NNgroup, Baymard, and repeated live YC critiques. Compiled 2026-08-08. **Confidence: moderate** — inconsistency, ambiguity, missing recovery information, and audience mismatch are observable; vocabulary frequency alone cannot prove AI authorship.

- **Hero-verb inflation is a comparison test, not a banned-word list.** Flag a headline dominated by generalized verbs or adjectives — for example “elevate,” “unlock,” “seamless,” or “powerful” — only when the same viewport fails to say what the product is, who it serves, what problem changes, or how it differs. Replace internal concepts with words the intended user uses. [field 2026-08-08][RynySryqM_0 3:32–3:53][RynySryqM_0 11:31–12:34]
- **An error must carry recovery information.** “Oops” or an apology is insufficient when the message omits what happened, what was affected, and what the user can do next; add amount, date, location, or retained-state details when they change the decision. [Yr2uIcFZDDQ 5:50 adjacent]
- Distinguish capability from value. “Analyze data quickly” describes an operation; the surrounding copy must connect it to the user outcome and identify the intended audience. A clever or aspirational headline needs a literal companion line when it cannot do this alone. [eMMiLeo_UGI][RynySryqM_0 3:32–3:53][RynySryqM_0 7:46–8:47]
- Audit voice, grammatical person, capitalization, product naming, units, and terminology across equivalent surfaces. “My account” beside “Your settings,” mixed button case, or two names for the same product is system drift when no contextual reason explains the change. [field 2026-08-08][RynySryqM_0 9:07–10:31][vv74GmBXxHE 8:38–9:00]
- Flag shipped placeholders and non-evidence: lorem fragments, template testimonials, an unexplained “your journey starts here,” stale affiliations, or social proof that does not say what relationship is being claimed. [field 2026-08-08][RynySryqM_0 16:03–16:43]
- Match jargon to the frame's defined audience. Specialist terms can be correct for experts; the finding arises when the target user cannot interpret the term and no plain-language label, example, or tooltip is supplied. [RynySryqM_0 2:30–3:32][vv74GmBXxHE 9:00–9:40]
- **Sentence slop is a compound quality finding, not an authorship detector.** For prose, require an adequate sample, at least two independent signal families, quoted evidence, and a demonstrated clarity, decision, recovery, specificity, conceptual-coherence, or intended-voice consequence. Sentence-length regularity, repeated openings, short-sentence bursts, rhetorical questions, formulaic scaffolds, paragraph-pattern reuse, passive candidates, transition concentration, phrase repetition, and detail sparsity may generate leads; none proves who wrote the text. [SADASIVAN23][MAGE24][ZANOTTO25][QUDSIM25]
- **Extract reader-facing prose before measuring it.** Remove frontmatter, HTML-only elements, image and badge markup, headings, tables, raw URLs, fenced or inline code, and install commands. Record the source-word and analyzed-word counts plus excluded structures. If that extraction cannot be verified, mark prose statistics not run; repository syntax is not sentence evidence. [field 2026-08-10]
- **Automated counts do not clear semantic slop.** For every adequate sample, manually trace metaphor and comparison mappings, test whether representative claims are portable across unrelated products, label each paragraph's task contribution, and compare the result with a supplied voice. Automated coherence models remain unreliable, so the script must expose this as a required human check rather than manufacture a semantic score. [COHESENTIA23][QUDSIM25][ORgKY9AlybA 10:36–14:36]
- **Count shared evidence once.** If repeated openings and a scaffold matcher quote the same four “not X, but Y” sentences, that is one rhetorical evidence cluster. Independent signal families currently include rhythm, rhetorical structure, discourse structure, lexical repetition, specificity, and responsibility. [field 2026-08-10]
- Do not use perplexity, “burstiness,” lexical predictability, or a stylistic probability as an AI verdict. Published stress tests show detector degradation under paraphrase and out-of-distribution conditions, while a study of seven detectors found an average 61.3% false-positive rate on its non-native English essay sample. Audit whether the words work for the product instead. [SADASIVAN23][MAGE24][LIANG23]
- **Cadence requires length and genre guards.** Prefer at least 150 words and five sentences for prose statistics; label 80–149 words limited and do not score a shorter sample. For UI fragments, compare at least eight equivalent strings or three related surfaces instead of applying paragraph metrics. Technical, legal, regulated, safety, translated, accessibility-simple, and supplied non-native contexts can legitimately use regular or constrained language. [LIANG23][W3C-READING]
- **Passive voice is a responsibility test, not a ban.** Flag it only when the user cannot tell who acted, what state changed, or how to recover — for example, “Your account was suspended” with no reason, actor, retained-state detail, or next step. Keep passive constructions when the actor is unknown, irrelevant, or appropriately deemphasized. [GOVUK-CLEAR]
- **Rhetorical construction becomes slop when it replaces information.** Repeated “What if…?”, “not X but Y,” “here is the truth,” transition-led sentences, or punchline fragments are findings only when they manufacture momentum while withholding the product, actor, condition, example, evidence, or decision the user needs. Parallel questions, em dashes, triads, fragments, parentheticals, and repetition remain legitimate teaching, genre, and comparison devices. [ORgKY9AlybA 4:06–8:32][ORgKY9AlybA 16:28–16:52]
- Never infer language background, disability, education, or writing assistance from prose. Plain, predictable, or grammatically constrained writing can be correct for its audience. Preserve clarity and accessibility even when a more flamboyant rewrite would appear more “human” to a detector. [LIANG23][W3C-READING]
- Cross-references: straight typewriter quotes (skill C1-5, [Butterick]); “corporate AI mush” and its fix [SfX43uIubj4 0:00].

**Rejected automatic tells:** exclamation marks, emoji in system copy, em dashes, triads, fragments, any single marketing verb or favorite word, passive voice by itself, a rhetorical question, short or regular sentences, low lexical variety, and the earlier ~7-word/~14-word hero budget do not independently establish a defect. Never report AI authorship or an AI probability from these features. Report the measurable ambiguity, conceptual collision, inconsistency, accessibility loss, voice failure, or task consequence instead.

**Canonical implementation ruling:** editorial slop is the public category; `copy` remains its durable registry key so published audit history does not break. Content strategy, terminology, microcopy, claims, provenance, information sequence, recovery language, voice, and sentence construction are review types inside that one category, not competing taxonomies. Author category labels, facets, and required receipts only in `schema/taxonomy.json` and `schema/audit-contract.json`; generated projections and validators must consume those manifests instead of copying the rules.

## 22. Performance slop — validated measurable axis

**Admission:** the field candidates were reconciled with current Core Web Vitals guidance and the Priority 2 wait-state demonstrations. Compiled 2026-08-08. **Confidence: high** for browser-measured LCP, CLS, and INP observations; **moderate** for perceived-wait design. Source inspection is a lead, not proof of field performance.

- Record field data when available and a reproducible lab trace otherwise. A performance finding names the affected route, device/network conditions, observed metric or blocking interval, implicated resource or task, and user-visible consequence. Do not infer “the backend is slow” from a spinner. [WEBDEV-LCP][WEBDEV-INP]
- **Hero-media slop is impact, not an arbitrary byte cutoff.** Identify the LCP element and resource, discovery delay, transfer size, and viewport fit. Keep likely LCP media discoverable in initial HTML; serve appropriate responsive variants with `srcset`/`sizes`. A good LCP target is at most 2.5 seconds at the 75th percentile. [WEBDEV-LCP][WEBDEV-RESPIMG]
- Reserve image/video space with intrinsic `width`/`height` or an equivalent `aspect-ratio`; missing dimensions are a common CLS cause. A good CLS target is at most 0.1 at the 75th percentile. [WEBDEV-CLS]
- Audit each webfont's necessity, fallback metrics, and explicit `font-display` behavior. The defect is invisible text, disruptive reflow, or needless critical-path cost — not the mere use of a webfont. [MDN-FONTDISPLAY][WEBDEV-CLS]
- **A spinner is not progress.** For short work, acknowledge immediately and preserve focus. For longer work, show truthful stages or partial results, state whether input is required, expose failure/timeout/retry, and provide a return notification or resumable path when the user should leave. Random looping messages and duplicate spinners are distraction, not status. [B7k5rOgmOGY 7:45][RynySryqM_0 30:49–32:32][DBhSfROq3wU 20:15–21:40]
- Measure third-party JavaScript by request cost, main-thread time, and render/interaction delay; remove it when it adds no clear value, otherwise keep it off the critical path with an appropriate loading strategy. “Third party” alone is not a finding. [WEBDEV-3P]
- Use current responsiveness evidence: a good INP is at most 200 ms at the 75th percentile; above 500 ms is poor. The earlier blanket “over 400 ms” rule is retired. Slow interactions still require immediate acknowledgment when the operation itself must continue. [WEBDEV-INP]

**Rejected automatic tells:** a multi-megabyte asset, `font-display: swap`, or a third-party script can be legitimate in context. Severity follows measured delay, instability, interaction blockage, affected traffic, and task consequence.

## 23. System-first generation and residue checks — Sergei Chyrkov pilot

**Admission:** three of three scoped videos showed the same system-before-screen, inspect, iterate, and verify method. Distilled 2026-08-08. **Confidence: moderate** — the observed failures are concrete, but the channel is tool-tutorial content and several visual conclusions are taste-led.

- **Uncontrolled token residue is an inspectable AI tell.** Flag a generated surface when its source contains a long tail of near-duplicate spacing values, corner radii, type styles, colors, or layout numbers instead of a small intentional scale. The defect is not “AI touched this”; it is that equivalent roles do not resolve to shared variables. [1MdwweKCNwg 0:00–0:42][1MdwweKCNwg 1:43–2:04]
- Put the constraint system before the screen: primitive and semantic colors, spacing scale, radii, borders, typography, and role aliases should exist before generation, and the generation instruction should name that source as binding. Asking the model to invent the system while composing the page produces superficially plausible but structurally incoherent output. [1MdwweKCNwg 2:26–4:08][1MdwweKCNwg 6:54–7:15]
- **A claimed design-system match is not evidence.** Inspect representative elements and compare their bound values with the source token file. In the demonstrated “exact” result, spacing and radii matched while the H1 silently used the wrong font; partial conformance must be reported as partial. [1MdwweKCNwg 8:15–9:20]
- Operate the generated interface before praising its polish. The first-pass pizza builder looked acceptable, yet one choice did not change and an apparent drag interaction was unavailable. Visual improvement cannot clear behavioral defects. [T96O8dTzi2Q 2:28–3:49]
- Treat design-to-code transfer as a lossy boundary. Compare the imported result against the live reference, then recheck typography, text integrity, motion, and behavior after every round trip; the pilot lost its font during import and later broke heading text while adding motion. [1d8vM0TXcTo 6:57–7:39][1d8vM0TXcTo 10:47–11:07]
- Keep alternatives or a branch until the live result is verified. Generating variants, reviewing them side by side, isolating the change, and inspecting the deployed page makes the decision reversible and exposes transfer drift. [1d8vM0TXcTo 9:03–10:26][1d8vM0TXcTo 13:34–14:58]

**Conflict ruling:** turning a reference image into a generated “design system” can produce stylistic consistency [T96O8dTzi2Q 4:30–7:34], but it does not establish semantic tokens, correct bindings, usability, or originality. It remains a visual hypothesis until source bindings and behavior pass inspection; §25's larger-system evidence strengthens this stricter ruling.

## 24. Specific direction, state economy, and alternative testing — DesignCourse pilot

**Admission:** three of three scoped videos repeatedly compared raw AI output with directed or manually refactored alternatives. Distilled 2026-08-08. **Confidence: moderate** — the structural observations are repeatable; palette, “fun,” and other aesthetic preferences remain uncompiled taste.

- The existence of a generated design system does not make the result distinctive. Inspect and edit its voice, primary/accent/semantic colors, component examples, and repeated motifs before using it; the demonstrated first system still produced a generic page until direct human changes were made. [YSYqFBq68Wk 5:50–7:15][YSYqFBq68Wk 8:38–12:29]
- A one-shot generation is a draft, not a design decision. Require a named direction, inspect the first output for specific misses, and iterate with bounded changes or alternatives. The pilot's claimed non-slop result took several follow-up prompts and roughly an hour of directed work. [YSYqFBq68Wk 13:10–14:33][YSYqFBq68Wk 17:40–18:23]
- **State narrated twice is clutter.** When an icon or badge already communicates online/active/default/runtime state, duplicate text or tags must add information or be removed. Repetition is not clarity when every copy says the same fact. [q1lGlhRnzsM 1:01–1:23][q1lGlhRnzsM 3:48–4:50]
- State signals must survive their background and sit where the eye can compare them. A tiny low-contrast check or a status dot directly against an uncontrolled avatar is fragile; use sufficient contrast, consistent alignment, and separation from unpredictable imagery. [q1lGlhRnzsM 1:23–1:44][q1lGlhRnzsM 2:05–3:26][q1lGlhRnzsM 4:50–5:11]
- Container count is a test, not a style ban. If a card adds only padding and border around already-related controls, remove it and compare readability and usable width. Keep the container when it carries grouping, selection, drag, or click semantics. [q1lGlhRnzsM 6:53–7:34]
- Repeated model defaults can be detected across outputs: unrelated domains receiving the same palette, repetitive section treatment, or literal obvious symbolism are corpus-level evidence of regression to the mean. They are not enough to convict a single app without in-app evidence. [0_PuRInJFrc 2:24–3:06][0_PuRInJFrc 6:10–6:53][0_PuRInJFrc 9:00–10:01]

**Counterexample ruling:** gradients, a particular primary color, or a creator's preferred visual alternative are not defects by themselves. Promote only the measurable failure underneath — contrast, duplication, hierarchy, unreadability, lost space, or cross-output sameness.

## 25. Design-system conformance is a binding audit — UI Collective pilot

**Admission:** four of four scoped videos repeated context scoping, production-reference research, binding inspection, QA, and drift-audit procedures. Distilled 2026-08-08. **Confidence: high** for the demonstrated conformance failures; **moderate** for workflow-efficiency prescriptions because the channel sells training and repeatedly promotes an affiliated reference product.

- **Connected is not bound.** A library can be present while generated elements ignore variables and type styles, override a component fill, substitute the wrong component, or invent a value. Inspect actual bindings; do not accept the tool's “design system connected” state as proof. [guRNce9XMp4 0:00–2:45]
- Audit for **invented and missing system content**: raw literals, added type styles, renamed semantic states, omitted disabled or other variants, invented avatar colors, and incomplete component sets. Importing a large source can create both hallucinations and silent omissions. [gIvxgXRGGpk 28:35–30:38]
- Scope system context by coherent component groups and include each component's variants, properties, documentation, and when-to-use rules. A broad “study all components” instruction loses coverage; a component name without its variants is a flattened contract. [guRNce9XMp4 3:07–8:14][gIvxgXRGGpk 24:09–27:34]
- Token names and values are insufficient when several tokens could render the same color. Supply semantic descriptions and light/dark or responsive roles so the audit can distinguish `surface.page` from `surface.default`, or desktop spacing from mobile spacing. [guRNce9XMp4 11:38–14:44][guRNce9XMp4 24:03–25:25]
- QA the context package at two levels: a narrow component request and a realistic multi-screen flow. Passing “build a form” while failing to reuse the same inputs in onboarding means the system context is still defective. [guRNce9XMp4 8:34–9:36]
- Organize reference evidence by competitor, feature, flow, or layout and compare the same task with and without that packet. The useful outcome is a better first draft, not a claim that reference-fed output is finished or correct. [nbk0PMS0tos 7:35–10:19]
- Record accepted design-system debt and organization-specific usage rules. Without that overlay, an audit repeatedly raises known unfixable exceptions or invents generic rules where the organization has made a deliberate tradeoff. This input requires human ownership; the model cannot infer it from the library. [guRNce9XMp4 20:15–23:42]
- Preview generated structures locally before inserting them into the canonical design file; once approved, reuse existing atoms, encode real variants/properties, forbid duplicate components, inspect bindings, and run a separate drift audit. Generation and its audit are two distinct passes. [gIvxgXRGGpk 35:47–40:12][gIvxgXRGGpk 40:34–41:16]
- Prefer task-relevant shipped flows over speculative gallery shots when selecting reference evidence, and never copy a source one-to-one. Production examples raise the feasibility prior; they do not prove the copied treatment fits a different product. [4vItmdk8F_M 1:21–1:43][4vItmdk8F_M 6:32–7:12]

**Conflict ruling:** §23 demonstrates that a compact, explicit JSON token contract can improve conformance; this section demonstrates that connecting or importing a larger system can still omit, rename, override, or invent content. Final rule: system context is useful input, never self-authenticating evidence. Audit the bindings and behavior.

## 26. Meaningful findings, adaptive paths, and implementable specs — NNgroup pilot

**Admission:** four of four scoped videos were piloted. Each provided a complete operational method despite course-preview framing. Distilled 2026-08-08. **Confidence: high** for the finding, CTA, and spec contracts; these extend, rather than replace, the standing Nielsen heuristics.

- A finding needs **observation + context + user impact + violated heuristic**. “The spinner gives insufficient status” is an opinion; duration, missing feedback, resulting uncertainty, and the relevant heuristic make it actionable. Keep the diagnosis separate from the remediation. [odk2fkPNVRA 0:43–1:45]
- Finding count is not thoroughness. Prioritize problems that interfere with understanding or task completion; omit or demote nuisances that merely prove the reviewer noticed them. A disproportionately large wrapping heading affected scanning, while two minor byline details did not merit equal attention. [odk2fkPNVRA 1:45–3:49]
- Test both cautious first-time and confident repeat use. Good flexibility means a clear default path plus optional shortcuts, presets, or automation — multiple paths to the same successful outcome, not more features. [WmmBLgtkjN4 0:00–2:03]
- A CTA should communicate **action, expected result, and value**. Start with a concrete verb, name what the click does or where it leads, and ensure the surrounding context supplies a reason to act. Generic “Learn more” or “Get started” is a finding when the destination or outcome remains ambiguous, not merely because those words appear. [UR8jF5xqjnk 0:44–2:29][UR8jF5xqjnk 3:31–5:35]
- When a CTA requests sensitive or consequential input, explain how that input produces the promised result. “Get a car insurance quote” adjacent to the ZIP field establishes a clearer exchange than a generic submit label. [UR8jF5xqjnk 2:51–3:11]
- A design is not implementable from appearance alone. Its spec must cover functionality, behavior, interaction flows, layout and breakpoints, content, accessibility needs, goal, scope, functional and non-functional requirements, and known risks or mitigations. Missing categories are a handoff gap, not permission for the implementer or model to guess. [mqNSTz5sX6E 0:23–1:46]
- The implementation contract has two linked views: the design artifact and the development issue. Keep the issue bounded and contextual; annotate screen relationships and flows in the design so behavior is traceable across states. [mqNSTz5sX6E 2:07–2:49]

**Severity ruling:** visual dislike cannot become a usability finding without a user consequence. Keep it at the visual layer unless it demonstrably harms scanning, comprehension, control, or task completion.

## 27. AI-assisted accessibility still ends in human validation — Deque Systems pilot

**Admission:** four of four scoped videos were piloted. Distilled 2026-08-08. **Confidence: high** for the interactive-element, keyboard, and measurement inventory because it maps to current W3C material; **moderate** for agentic-modality extensions, which the source itself describes as emerging. Deque is a vendor, so product-efficiency claims are excluded. The fourth video is from 2018: its WCAG-version and legal-jurisdiction advice is obsolete and was not promoted.

- If an agent or conversational workflow is a supported way to use the product, it is part of the accessible product experience. Users must understand what it can and will do, issue instructions, review output, correct mistakes, confirm consequential actions, and recover from errors. [Yps3BHLE0yY 12:20–13:00]
- Test generated content and agent-enabled workflows across the scenarios and modalities users actually depend on. Text alone is not the boundary: generated tables, graphics, and personalized components remain subject to accessibility requirements. An inference is acceptable only relative to an explicit error rate and context, not because the model can usually do it. [Yps3BHLE0yY 13:43–19:45]
- For every interactive element, verify accessible **name, role, value, and applicable states**. AI-generated pass/fail output should expose its reasoning and remains provisional until a reviewer validates representative results and resolves disagreements. [LaS00N9pOt0 0:00–2:26]
- A keyboard check must perform a real tab walk and inspect visible focus, purpose/role, focus-state contrast, automatic submission on focus, and traps. A DOM scan or “keyboard accessible” claim without this walk is not evidence. [CZ0SG4pH-yM 0:01–1:46]
- Keep the human override. The demonstrated automated tests explicitly end in review, with the reviewer able to flip a false pass or false failure. Automation scales the guided test; it does not remove accountability for the result. [CZ0SG4pH-yM 1:05–2:07][LaS00N9pOt0 1:23–2:26]
- Measure conformance against the applicable **success criterion and conformance requirements**, not a vague principle or one prescribed implementation technique. W3C techniques are informative ways to meet a criterion, not the criterion itself. [_eDRLi0C6a4 7:00–10:30][_eDRLi0C6a4 23:09–24:33][WCAG22]
- Start with keyboard-only operation, programmatic form labels, and an automated scan because they expose common barriers quickly; never present that starter set, or any “top ten,” as complete coverage across disability types. [_eDRLi0C6a4 12:22–17:41][_eDRLi0C6a4 44:37–45:41]
- Automated tools can reliably identify some syntactic absences but not whether supplied content is appropriate — for example, missing alt text versus useful equivalent alt text. No tool alone determines accessibility; knowledgeable human review remains required. [_eDRLi0C6a4 52:14–53:40][W3C-EVAL]
- Prioritize by the impact of a failed feature on a person completing the task, not by an estimate of how many users with a named disability visit the product. [_eDRLi0C6a4 48:37–49:40]
- Label compliance and best practice separately. A nonconformance finding names the exact normative requirement; advice that cannot be tied to one remains an openly labeled best practice or usability recommendation. [_eDRLi0C6a4 56:08–57:13][WCAG22]

**Counterexample ruling:** not every AI output is interactive, and not every action should be autonomous. Apply name/role/state checks to interactive elements; require confirmation in proportion to consequence, privacy, reversibility, and error cost. [Yps3BHLE0yY 6:22–10:35]

**Freshness ruling:** current W3C guidance recommends WCAG 2.2 as the conformance target and explicitly distinguishes normative requirements from informative supporting material. The 2018 video's WCAG 2.0/2.1 rollout and jurisdiction predictions are historical context only; they cannot drive a current audit. [WCAG22]

## 28. SaaS flow, data depth, and feasibility checks — Eleken pilot

**Admission:** four of four scoped videos repeated task-first flow review, hierarchy, progressive disclosure, and audit-before-redesign. Distilled 2026-08-08. **Confidence: moderate** — the demonstrated procedures are operational, but the channel is an agency and its client outcomes were not independently verified. Where the videos merely restated Nielsen heuristics, this section records corroboration rather than inventing another rule.

- Begin a SaaS audit with the intended user, scenario, and key flow. Walk the path and capture the current states before changing visual treatment; a screen-by-screen redesign without a flow map can polish the wrong problem. [QtgCnSWZkt4 0:00–1:45][JGmcG1vRmuw 5:30–6:53]
- Check whether action, content, and navigation have distinguishable visual priority and whether the same action behaves consistently across the flow. When the action set overwhelms the decision, preserve a clear primary path and disclose secondary or expert controls progressively. [K8yLcutmp-M 0:00–0:40][K8yLcutmp-M 1:42–2:24][K8yLcutmp-M 3:27–4:07]
- For data-heavy products, derive information architecture from user intents and questions, not from the available fields. Present the high-level answer first and put evidence, filters, and configuration beneath or on demand. “Show everything” is not neutral; it transfers the data-model burden to the user. [rP-I4Oihqc8 0:00–1:23][rP-I4Oihqc8 1:44–2:45]
- When novice and expert needs differ, test a guided standard path and a configurable advanced path against the same outcome. Do not make every user traverse expert controls, and do not erase expert depth to simplify the default. [rP-I4Oihqc8 2:49–3:48]
- Treat implementation feasibility as a recorded tradeoff, not a yes/no veto. For a visually elaborate proposal, capture user value, implementation cost, maintenance surface, performance/accessibility risk, and likely defect burden before recommending it. [K8yLcutmp-M 2:24–2:44]
- A learned workaround does not clear a confusing interface. Users can adapt to inconsistent controls or weak hierarchy; the audit still records the avoidable effort and task risk. [K8yLcutmp-M 3:05–3:27]

**Conflict ruling:** these sources strengthen §§1–4, §14, and the Nielsen floor. Their agency-reported conversion, retention, or business improvements are excluded unless the audit obtains the underlying study design or product analytics.

## 29. Native semantics and composite-widget state — Kevin Powell pilot

**Admission:** three of three scoped videos demonstrated recurring implementation checks against live markup and keyboard behavior. Distilled 2026-08-08 and reconciled with current W3C WAI guidance. **Confidence: high** for native-element, focus, hidden-state, alt-text, and tabs-pattern checks; creator tool promotions and incidental demo architecture are excluded.

- Prefer the native element whose semantics and behavior match the action. A clickable `div` does not become a button by appearance or `role="button"`; the implementation must recreate focusability, accessible role/name, click, Enter, Space, disabled behavior, and state. The role is a promise, not behavior supplied by ARIA. [YAqRQoN8ykI 1:21–3:05][WAI-APG]
- Inspect the document outline and landmark structure before adding ARIA: meaningful headings plus native `main`, `nav`, and other landmarks give navigation structure, while native `details`/`summary` can supply disclosure behavior without a bespoke script. [pJ0GPI7BMIs 1:23–5:10]
- An automated image check distinguishes missing alt from present alt; it cannot determine whether the text conveys the image's purpose in this context. Decorative images use `alt=""`; functional images name the action or destination; important contextual information comes first. [pJ0GPI7BMIs 6:53–12:28][WAI-ALT]
- Perform a real keyboard walk. Verify visible focus, logical order, an efficient path past repeated navigation, hover content reachable by keyboard, and native controls instead of focusable impostors. A skip link must be the first relevant focus stop, become visible on focus, and move focus or navigation to the main content. [pJ0GPI7BMIs 16:34–25:09]
- Icon-only controls and links require a discernible accessible name. A visible glyph, SVG path, or tooltip that only appears on pointer hover does not by itself establish the control's name. [pJ0GPI7BMIs 25:30–27:10]
- A disclosure or menu state is one synchronized contract: the controlling button sits next to the controlled region, exposes an accessible name and `aria-expanded`, and updates the visual state, accessibility state, and focusability of hidden content together. Off-screen or clipped content that remains tabbable is not closed. [YAqRQoN8ykI 3:48–9:13][YAqRQoN8ykI 12:03–23:19]
- Before implementing tabs, test whether headings plus ordinary scrolling or in-page links expose the content more clearly. If tabs remain justified, preserve a functional no-script baseline where feasible and verify the current APG contract: `tablist`/`tab`/`tabpanel`, one selected tab, correct labels/relationships, roving focus, arrow navigation, and Enter/Space for manual activation. `aria-controls` describes a relationship; it does not switch panels. [fI9VM5zzpu8 0:50–5:06][fI9VM5zzpu8 17:45–33:10][fI9VM5zzpu8 39:04–50:15][WAI-TABS]
- Standards-conforming widget code is still a hypothesis until exercised with keyboard and relevant browser/assistive-technology combinations. Add extra screen-reader instructions only when testing shows they help; repeated verbose hints can create new friction. [fI9VM5zzpu8 26:30–29:42][fI9VM5zzpu8 36:40–38:53][WAI-APG]

**Counterexample ruling:** custom ARIA widgets are legitimate where HTML has no equivalent and the interaction earns its complexity. The finding is an unfulfilled semantic/behavior contract, not the mere presence of a `div`, JavaScript, or ARIA.

## 30. Engagement mechanics require a user-value and harm contract — Tim Gabe pilot

**Admission:** four of four scoped videos applied the recurring lens “mechanic → user feeling/behavior → product outcome,” clearing repeatability for audit questions. Distilled 2026-08-08. **Confidence: moderate** for the harm and agency checks; **low** for the channel's causal business claims. The videos are agency marketing and frequently present uncited statistics, so no quoted retention, revenue, valuation, regulator, or population figure was admitted.

- For every streak, badge, leaderboard, reward, or celebratory animation, write the contract: target user behavior, trigger, feedback, user control, failure/loss consequence, and real user benefit. If the only measurable outcome is more app opens, taps, or purchases, label it engagement theater until a user-valued outcome is demonstrated. [LXX_qOA5D8E 1:08–2:31][LXX_qOA5D8E 9:14–12:00]
- Competition must be winnable and relevant to the participant. Test global and appropriately scoped comparison groups; a ranking that makes success feel impossible, exposes an unwanted identity, or pressures the user at a vulnerable moment is a harm risk, not a retention win. [BxhsCu9hNpY 1:05–2:49][LXX_qOA5D8E 2:31–3:56]
- Audit streaks for agency: user-chosen goal, pause/freeze, recovery after interruption, a clear exit, and no punishment disproportionate to the underlying task. Loss aversion, shame, or inability to recover raises the dark-pattern severity. [LXX_qOA5D8E 6:04–7:29]
- Recognition should evidence progress in the real activity. A badge for opening the app or producing volume can displace quality; competence feedback names what improved, against what baseline, and how the user can act on it. [LXX_qOA5D8E 1:08–2:31][LXX_qOA5D8E 10:38–12:00]
- Default onboarding to the shortest path that delivers tangible value. Every prerequisite screen must earn its place by enabling required permission, safety, or a materially better first result. A long funnel that merely filters out reluctant users may improve a business metric while harming task access; do not call that user success. [Aa89MC8jX2c 1:02–2:03][Aa89MC8jX2c 3:03–4:24]
- Put emotional motion at truthful feedback moments — completion, correction, progress, or recovery — and keep it proportional to the event. Polish, glow, mascots, or haptics cannot independently establish trust, retention, or safety, especially in consequential products. [Du2lkZ_cux8 3:27–5:13][Du2lkZ_cux8 7:41–8:44]

**Harm ruling:** optimize for the user's chosen outcome before the product's engagement metric. Any mechanic that changes money, privacy, health, access, social standing, or compulsive use requires stronger evidence, explicit control, and a reversible path.

## 31. E-commerce evidence must stay scoped to the shopping decision — Baymard Institute pilot

**Admission:** three of three scoped videos repeated an evidence chain from exact UI → observed user behavior → scoped recommendation → relevant implementation example. Distilled 2026-08-08. **Confidence: high** that the listed states are testable e-commerce risks; **moderate** for generalization because the underlying proprietary studies were not independently reproduced. Two videos promote Baymard products, so tool-speed and “95% accuracy” claims are excluded.

- Preserve the evidence chain. Name the exact implementation and shopping context, the observed or plausible decision barrier, the recommendation, and a comparable example from the same product type or industry. An AI mapper may retrieve candidate research for a screenshot; it must not invent the recommendation or expand e-commerce evidence into an unrelated product. [fuAdtcqLC6I 1:02–2:50][ss0jhpbAidc 1:21–2:45]
- On product pages, horizontal tabs can hide decision-critical content. Test a vertically collapsed or continuously scrollable alternative, ensure section labels remain scannable, and never infer that hidden content was seen merely because the tab exists. [vv74GmBXxHE 0:32–1:22]
- Product imagery must answer scale, fit, and real-use questions the buyer cannot inspect physically. Supply a known-size reference or relevant human model and make customer-submitted images navigable without abandoning the review context. [vv74GmBXxHE 1:33–3:28][vv74GmBXxHE 11:24–12:05]
- Keep the economic decision visible before cart commitment: unit price where quantities differ, lowest total-order or shipping estimate with conditions, and a clear return-policy summary/link. Let guests save comparison candidates unless account creation is genuinely required for the saved state. [vv74GmBXxHE 3:49–6:54]
- Comparable products need comparable specifications: group medium/long sheets under descriptive headings, normalize units and field names, and explain domain terms with plain labels or tooltips. A wall of specs is not expert density when the sought attribute cannot be found. [vv74GmBXxHE 7:32–9:40]
- Keep review collection focused on the specific product; unrelated account or service questions add submission cost. Make negative reviews and merchant responses visible, and let users move through reviewer media without losing their place. [vv74GmBXxHE 9:14–12:05]
- Separate quantitative prevalence from qualitative cause and interface guidance. “How many shoppers do this?” can prioritize a roadmap; it does not reveal why the behavior occurs or which implementation will fix it without linked qualitative evidence. [ss0jhpbAidc 0:00–2:45]

**Scope ruling:** these are shopping-decision checks, not universal website laws. Apply them to e-commerce or a demonstrably equivalent comparison/purchase task and label the proprietary research provenance.

## 32. AI interfaces expose work, uncertainty, and control — YC Design Review targeted series

**Admission:** the two scoped videos, together with the standing Steven Haney episode, establish a three-episode targeted-series pilot. Distilled 2026-08-08. **Confidence: moderate** — the evidence is repeated expert walkthrough, not controlled research. Never sweep unrelated YC uploads.

- Run a first-viewport comprehension test in this order: **What is it? Is it for me? Does it work? Is it credible?** Do not lead with investor logos, animations, or signup demands while the first two answers remain obscure. A playful headline needs literal support, and each viewport needs a deliberate primary action rather than a field of equally loud buttons. [RynySryqM_0 5:40–8:47][RynySryqM_0 9:07–9:49][RynySryqM_0 19:28–20:09]
- Audit craft across the boundary, not only the hero: alignment, hover behavior, media crops, icon meaning, token consistency, and continuity between marketing, product, pricing, and account surfaces. “Vibe coded” is not a finding; the disjointed state values and broken behavior are. [RynySryqM_0 1:28–2:09][RynySryqM_0 14:30–19:28][RynySryqM_0 20:40–22:33]
- For prompt-first interfaces, replace an empty canvas with task-relevant examples or inferred suggestions that can be accepted in one action. When vocabulary is specialist or open-ended, provide a structured prompt builder without removing free-form input. [DBhSfROq3wU 13:20–14:23][DBhSfROq3wU 19:29–22:42]
- Return a constraint ledger with generated output: which instructions were applied, ignored, uncertain, or impossible. Let the user revise the affected module or delta while preserving accepted output; whole-output regeneration for a local edit is a loss-of-control smell. [DBhSfROq3wU 22:42–25:04]
- Expose provenance beside generated claims and preserve units and context. A source link close to the value enables verification; a sourced “6.6” that drops “billion” is still wrong. [DBhSfROq3wU 15:46–18:51]
- Match wait treatment to latency. Short operations need immediate state acknowledgment; long operations need stable stages or a technical log appropriate to the audience, truthful duration/uncertainty, partial or lower-fidelity previews when useful, and a notification/resume path. Looping jokes or spinners without progress cannot substitute for this. [RynySryqM_0 30:49–32:32][DBhSfROq3wU 20:15–21:40][DBhSfROq3wU 32:32–34:34]
- In multimodal interfaces, pair voice/audio with visual listening, speaking, latency, interruption, and failure cues where a screen is available. Test interruption and correction, not just the happy-path voice quality. [DBhSfROq3wU 1:45–4:05][DBhSfROq3wU 4:57–7:31]
- Adaptive controls may change with context, but interaction anchors must remain predictable. Keep stable locations or shortcuts where possible, clearly distinguish typing focus from command mode, and never let an unmodified letter trigger a consequential action while text entry is ambiguous. [DBhSfROq3wU 25:24–30:09]
- Let a new user operate a constrained, reliable example before demanding signup when the experience can be safely trialed. If the model cannot support the open-ended demo reliably, narrow the first task rather than placing authentication in front of proof. [RynySryqM_0 30:30–35:15]

**Counterexample ruling:** hidden internal chain-of-thought is not required. Expose user-relevant stages, tool actions, sources, constraints, required confirmations, and recoverable state — not private reasoning or an indiscriminate wall of tokens.

## 33. Sentence slop lives above the token — research reconciliation

**Admission:** one supplied linguist video was transcribed and reconciled with a current Reddit community sample, Hank Green's primary public statement, and peer-reviewed work on prose variability, discourse similarity, coherence assessment, and detector bias. Compiled 2026-08-10. **Confidence: high** for rejecting single-tell authorship claims and excluding markup before measurement; **moderate** for the manual passage-review procedure; **low** for attributing any individual construction or passage to a model.

- Keep the surface bingo card as a lead generator only. Chipper validation, favorite words, contrast frames, fragments, em dashes, parentheticals, and triads can cluster in weak copy, but each also occurs in ordinary academic, advertising, tutorial, and creator writing. One construction cannot establish a quality defect or authorship. [ORgKY9AlybA 4:06–8:32][LIANG23]
- Look for **semantic fit across the passage**: whether the selected verbs can act on their objects, whether a metaphor preserves its source-to-target mapping, whether two familiar phrases contradict when combined, and whether each paragraph's conclusion follows from its claims. Quote the exact collision and restate the intended meaning. [ORgKY9AlybA 10:36–13:22][COHESENTIA23]
- Do not turn conceptual incoherence into an authorship verdict. Humans also mix metaphors and write confused prose; the product question is whether the passage works. When the meaning is materially obscured, report bad writing and its user consequence without deciding who or what produced it. [ORgKY9AlybA 13:22–14:36]
- Passage structure is more durable than a banned-word list. Current community discussions repeatedly describe a model settling into the same contrast, cadence, summary, and paragraph choreography over long samples; QUD-based research formalizes recurring discourse similarity across texts. This supports a paragraph-pattern review, not an individual-source classifier. [REDDIT-WRITING26][QUDSIM25]
- Specificity and subtext need direct evidence. Test whether a claim names the actor, object, condition, example, evidence, or consequence; test whether it could be pasted unchanged into unrelated products; and compare it with the product's supplied voice. “Generic,” “soulless,” and “sounds like AI” are not evidence records. [REDDIT-WRITING26][field 2026-08-10]
- Treat process trust separately from sentence style. Hank Green's statement distinguishes using AI to locate research, forming and expressing his own views, audience trust that the words are his, and a pattern of overreliance that he believed diluted his process. Those are provenance and editorial-process questions. Scruffy may audit visible sourcing, disclosure, claim support, and voice consistency; it cannot recover that process from punctuation. [HANKGREEN26]
- Use generation assistance where the result can be checked and edited, but keep a human accountable for claims, meaning, and final voice. Boilerplate, omission checks, trimming, and first drafts do not excuse conceptual collisions or unsupported claims in the shipped interface. [ORgKY9AlybA 14:38–16:28][HANKGREEN26]

**Implementation ruling:** `scripts/analyze_sentence_slop.py` performs markup-aware extraction and conservative surface measurement. Every adequate prose run must still complete the manual conceptual-coherence, portability, discourse-purpose, and voice/subtext checks in `references/sentence-slop.md`. The script never clears those checks and never reports authorship.

## 34. Published interaction laws — Laws of UX reconciliation

**Admission:** the standing `[LawsUX]` source row claimed Hick, Fitts, Miller, Doherty, and peak-end as distilled while only Fitts (§15), proximity (§11), and aesthetic-usability (§19) had operational rules; this section closes that drift. Reconciled 2026-09-02 against the current lawsofux.com law pages and the standing corpus: each admitted law either corroborates an existing section or adds an observable predicate with a false-positive guard. **Confidence: high** for the grouping, isolation, and feedback-acknowledgment observables (perception research with direct interface predicates); **moderate** for Hick and Miller leads (population-level effects — per-interface conviction still requires an observed task consequence); **low** for the literal 400 ms Doherty figure (1982 IBM terminal-productivity research; the current measured floor is Core Web Vitals). A law is a lead or a weighting rule, never a verdict by name-drop: the finding cites the observed consequence, not the law.

- **Hick's law — choice-set size at decision moments.** Count the same-weight choices actually exposed where the user must pick (nav, action menus, pricing, onboarding forks). A lead fires when options are many, undifferentiated, and carry no default, recommendation, or grouping; conviction needs an observed cost — hesitation in the walk, wrong-path selection, or an abandonment-shaped structure. Guards: dense operational surfaces legitimately expose many controls (§13 density rule); the source itself warns against simplifying to the point of abstraction; sequenced disclosure (§2) is the standing remedy, not deletion of capability. [LawsUX]
- **Miller's law — chunk, don't cap.** The violation is absent structure, never count > 7 by itself: unsectioned nav runs, ungrouped form fields (§13), digit strings rendered without grouping, six-bullet onboarding dumps (§2). The source's own first takeaway forbids using "the magical number seven" to justify design limitations, and the working-memory literature it links puts the practical span nearer four chunks — cite the missing grouping and the scan or recall cost, not a number. [LawsUX]
- **Jakob's law — convention transfer.** Users import mechanics from the products they already spend their time in; an unfamiliar mechanic doing a familiar job is a lead. It binds to the standing grounding guards before conviction: pull comparable shipped screens, and deviation convicts only with observed task friction, comprehension cost, or trust cost, while matching convention clears nothing harmful (`references/reference-grounding.md`). For deliberate breaks, the source's remedy is a reversible transition users can defer, not a frozen design. [LawsUX]
- **Von Restorff effect — isolation economy.** One differentiated treatment per decision moment: the intended primary action or exception should be the only element breaking the local pattern — corroborating one-primary-CTA and exceptions-louder-than-reassurance (§4, §13). Audit both failures: no isolation (everything equally loud, nothing registers) and isolation inflation (competing emphases). Guards: the difference cannot ride on color alone (§27), motion-borne emphasis needs a reduced-motion path, and an over-styled salient block reads as an ad and gets banner-blinded. [LawsUX]
- **Doherty threshold — the acknowledgment contract.** Every interaction acknowledges within ~400 ms — a state change, optimistic UI (§3), skeleton, or honest progress — and measured input responsiveness already has a stricter floor (INP "good" ≤ 200 ms), so 400 ms is the outer bound for visible acknowledgment, not a pass. Guards: a fabricated or looping progress indicator is a trust finding, not a remedy (§21); an honest deliberate delay that communicates real work — the source's own perceived-value takeaway — is not a violation when the work is real. [LawsUX][WEBDEV-INP]
- **Common region & uniform connectedness — containment outranks proximity.** A border, background, or explicit connector asserts stronger grouping than spacing, so audit both directions: unrelated items sharing a container claim a false relationship; related controls split across regions hide one. Guard: container economy stands (§11, §13 fewer-containers rule) — when whitespace already communicates the group, adding a box to satisfy the law is itself slop, and a connector carries meaning only when the connection is real (flow order, data lineage). [LawsUX]
- **Peak-end rule — flow-judgment weighting.** Users judge a flow by its worst moment and its final step, so audit both explicitly: the end state of every core flow (confirmation, recovery, next action) and the single worst interaction, with an equivalent defect at the last step outranking one mid-flow. Guard: this weights attention and severity, it exempts nothing — mid-flow findings keep their evidence-based severity. [LawsUX]

**Not admitted, recorded so they are not re-litigated:** *Postel's law* (contested network-protocol robustness doctrine; no interface predicate), *Parkinson's law* (organizational time behavior; nothing observable in a shipped surface), *Occam's razor* and the *Pareto principle* (reasoning heuristics for the auditor, unfalsifiable as per-finding rules), *Tesler's law* (real conservation-of-complexity vocabulary for design tradeoffs — names a constraint, not a defect), *serial-position effect* (subsumed by §13 ordering and the peak-end weighting above), *Zeigarnik* and *goal-gradient* effects (real memory and motivation effects whose interface applications — streaks, progress bait, incomplete-task nagging — are exactly the engagement mechanics that must pass §20/§30's user-value and harm contract rather than enter as "show progress" prescriptions), and *Prägnanz*, *similarity*, and *closure* as standalone rules (their operational content already lives in the grouping and consistency rules of §4, §11, §13, and the bullets above). *Fitts's law*, the *law of proximity*, and the *aesthetic-usability effect* were already operational (§15, §11, §19); the `[LawsUX]` source row now points here instead of overclaiming.
