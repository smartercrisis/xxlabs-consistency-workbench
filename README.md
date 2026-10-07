XX_LABS BTA Workbench

Deterministic brand-governance workbench. No LLM calls, no API keys, no cost per use.
Verification runs on the prompt, not the pixels.

What it does
1. Forge Anchor — interview form produces a versioned `brand_anchor.json` (SHA-256 hash of the canonical JSON = any parameter change changes the hash).
2. Govern Brief — paste a messy brief; three deterministic steps run: Input Isolation (filler purge) → Negative Constraint Purging (banned colors/competitors) → Parameter Locking (per-engine prompt assembly: Midjourney / Runway / Kling / Universal).
3. Lexical gate — real PASS/FAIL: forbidden-token scan, approved-channel lock, Kelvin range check, subject-presence check. A gate that always passes is worse than no gate — this one doesn't.
4. Telemetry sidebar — session counters (governed briefs, purged terms, FAIL verdicts) + live color swatches, Kelvin lock, anchor hash.

Default anchor
Pre-loaded with the XX Labs master anchor (BTA-XXL.01): Radeon-style hardware vectors,
sine-wave geometry overlays, crimson/green/gold channels, brushed titanium, nuclear-core
processors, 3200K–5600K lighting lock. Edit or replace via the uploader in the sidebar.

Governance version: CIAT25.1 — 7 gates + 2 support layers.
