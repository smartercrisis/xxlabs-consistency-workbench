"""
XX_LABS BTA Workbench — Deterministic Brand Governance (CIAT25.1-flavored)
No LLM calls. No API keys. Verification runs on the PROMPT, not the pixels.
Deploy free: github repo + share.streamlit.io
"""
import json
import re
import hashlib
import datetime
import streamlit as st

st.set_page_config(page_title="XX_LABS BTA Workbench", page_icon="⬡", layout="wide")

# ============================================================
# DEFAULT MASTER ANCHOR — BTA-XXL.01 (XX Labs brand)
# ============================================================
DEFAULT_ANCHOR = {
    "anchor_id": "BTA-XXL.01",
    "anchor_name": "XX Labs Master Anchor",
    "governance_version": "CIAT25.1",
    "tone": "Authoritative, direct, uncompromising, professional.",
    "vectors": {
        "alpha": {
            "title": "Vector Alpha — Radeon Hardware Industrial",
            "description": ("Ultra-realistic 3D industrial hardware assemblies, futuristic processors "
                            "with visible nuclear cores, AMD Radeon-inspired engineering aesthetic, "
                            "brushed titanium surfaces, layered holographic overlays, sine-wave frequency "
                            "graphs, high-mass geometric tracking patterns, razor-sharp physical detail, "
                            "dynamic composition primed for motion-start framing.")
        },
        "beta": {
            "title": "Vector Beta — Kinetic Anime Build",
            "description": ("High-impact anime styling calibrated to Vector Alpha's hardware and energy "
                            "architecture, kinetic fighting-game character builds, stylized energy auras "
                            "in approved color channels.")
        }
    },
    "color_channels": {
        "active": [
            {"name": "illuminating green", "hex": "#00FF7F"},
            {"name": "royal gold", "hex": "#D4AF37"},
            {"name": "crimson red", "hex": "#DC143C"}
        ],
        "forbidden": ["laser blue", "neon blue", "generic blue glow", "electric blue", "cyan glow"]
    },
    "kelvin_range": {"min": 3200, "max": 5600},
    "materials": ["brushed titanium", "nuclear core glow inside processors", "machined aluminum edges"],
    "geometry_overlays": ["sine-wave frequency graphs", "high-mass geometric patterns"],
    "filler_phrases": [
        "make it look cool", "make it pop", "make it stand out", "hyper-realistic", "super detailed",
        "ultra hd", "8k", "masterpiece", "best quality", "very", "really", "extremely", "awesome",
        "epic", "stunning", "amazing", "beautiful", "cool", "nice", "modern look", "sleek", "fancy",
        "wow factor", "eye-catching", "trendy", "cinematic look", "professional looking",
        "make a", "make an", "make me", "create a", "create an", "generate a", "generate an",
        "please", "can you", "could you", "i want", "i need", "hey", "hello"
    ],
    "forbidden_elements": ["competitor references", "parody framing", "style drift artifacts", "vague modifiers"],
    "competitor_names": [],
    "default_aspect": "16:9"
}

def normalize_anchor(a: dict) -> dict:
    if not isinstance(a, dict):
        return DEFAULT_ANCHOR.copy()
    
    normalized = DEFAULT_ANCHOR.copy()
    normalized["anchor_id"] = a.get("anchor_id") or a.get("id") or "BTA-CUSTOM.01"
    normalized["anchor_name"] = a.get("anchor_name") or a.get("name") or a.get("title") or "Custom Anchor"
    normalized["governance_version"] = a.get("governance_version") or a.get("version") or "CIAT25.1"
    normalized["tone"] = a.get("tone") or a.get("brand_tone") or DEFAULT_ANCHOR["tone"]
    
    vecs = a.get("vectors") or a.get("style_vectors")
    if isinstance(vecs, dict) and vecs:
        normalized["vectors"] = vecs
        
    cc = a.get("color_channels") or a.get("colors")
    if isinstance(cc, dict):
        normalized["color_channels"] = cc
    elif isinstance(cc, list):
        normalized["color_channels"] = {"active": cc, "forbidden": []}
        
    kr = a.get("kelvin_range") or a.get("kelvin")
    if isinstance(kr, dict):
        normalized["kelvin_range"] = kr
        
    for key in ["materials", "geometry_overlays", "filler_phrases", "forbidden_elements", "competitor_names"]:
        if key in a and isinstance(a[key], list):
            normalized[key] = a[key]
            
    if "default_aspect" in a:
        normalized["default_aspect"] = a["default_aspect"]
    elif "aspect_ratio" in a:
        normalized["default_aspect"] = a["aspect_ratio"]
        
    return normalized

# ============================================================
# DETERMINISTIC CORE
# ============================================================
def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)

def anchor_hash(anchor: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(anchor).encode("utf-8")).hexdigest()[:12]

def _phrase_escape(p: str) -> str:
    return re.escape(p.strip())

def purge_filler(text: str, anchor: dict):
    removed, cleaned = [], text
    for phrase in sorted(anchor.get("filler_phrases", []), key=len, reverse=True):
        pattern = re.compile(r"\b" + _phrase_escape(phrase) + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            removed.append(phrase)
            cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;."), removed

def purge_banned(text: str, anchor: dict):
    banned = list(anchor.get("color_channels", {}).get("forbidden", [])) + \
             list(anchor.get("competitor_names", []))
    removed, cleaned = [], text
    for term in sorted([b for b in banned if b.strip()], key=len, reverse=True):
        pattern = re.compile(r"\b" + _phrase_escape(term) + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            removed.append(term)
            cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;."), removed

def lock_parameters(intent: str, anchor: dict, vector_key: str, asset_type: str,
                    platform: str, aspect: str, kelvin: int):
    vectors = anchor.get("vectors", DEFAULT_ANCHOR["vectors"])
    vec = vectors.get(vector_key, list(vectors.values())[0])
    colors = ", ".join(c["name"] for c in anchor.get("color_channels", {}).get("active", []))
    hexes = ", ".join(c["hex"] for c in anchor.get("color_channels", {}).get("active", []))
    mats = ", ".join(anchor.get("materials", []))
    geo = ", ".join(anchor.get("geometry_overlays", []))
    k = anchor.get("kelvin_range", {"min": 3200, "max": 5600})
    kelvin = min(max(kelvin, k.get("min", 3200)), k.get("max", 5600))
    base = (f"{intent} — {vec.get('description', '')} Color channels: {colors} ({hexes}). "
            f"Lighting locked at {kelvin}K. Materials: {mats}. Overlays: {geo}.")
    negatives = ", ".join(anchor.get("color_channels", {}).get("forbidden", [])[:3] +
                          ["style drift", "brand dilution", "generic filler"])
    if platform == "Midjourney":
        prompt = f"{base} --no {negatives} --ar {aspect.replace(':', ':')}"
    elif platform in ("Runway", "Kling"):
        motion = ("Slow orbital camera move, motion-start framing, energy pulses traveling "
                  "through the geometric overlays in approved color channels only.")
        prompt = f"{base} {motion}" if asset_type == "motion" else base
    else:
        prompt = base
    if asset_type == "copy":
        prompt = (f"[COPY BRIEF | tone: {anchor.get('tone', '')}] Subject: {intent}. Voice: locked to anchor. "
                  f"Forbidden: {', '.join(anchor.get('forbidden_elements', []))}.")
    return prompt, negatives, {"kelvin_locked": kelvin, "aspect": aspect, "vector": vec.get("title", vector_key)}

def validate(intent: str, prompt: str, anchor: dict, removed_banned, asset_type: str = "still"):
    checks = []
    checks.append(("Subject preserved", bool(intent), "asset_intent empty after scrubbing — BLOCKED"))
    body = prompt.split("--no")[0].lower()
    leaks = [t for t in anchor.get("color_channels", {}).get("forbidden", [])
             if re.search(r"\b" + re.escape(t.lower()) + r"\b", body)]
    checks.append(("Zero forbidden color channels (positive body)", not leaks, f"leaked: {leaks}" if leaks else "clean"))
    comps = [t for t in anchor.get("competitor_names", []) if t and t.lower() in body]
    checks.append(("Zero competitor references", not comps, f"found: {comps}" if comps else "clean"))
    checks.append(("Style vector locked", "—" in prompt or "[COPY BRIEF" in prompt, "vector description embedded"))
    if asset_type == "copy":
        tone_ok = anchor.get("tone", "").split(",")[0].strip().lower() in body
        checks.append(("Tone lock embedded", tone_ok, "anchor tone in brief header"))
    else:
        active = [c["name"] for c in anchor.get("color_channels", {}).get("active", []) if c["name"].lower() in body]
        checks.append(("Approved color channel locked", len(active) >= 1, f"locked: {active}"))
        kr = anchor.get("kelvin_range", {})
        m = re.search(r"(\d{4})K", prompt)
        kelvin_ok = bool(m) and kr.get("min", 0) <= int(m.group(1)) <= kr.get("max", 9999)
        checks.append(("Kelvin within lock range", kelvin_ok,
                       f"{m.group(1)}K in {kr.get('min')}–{kr.get('max')}K" if m else "no Kelvin value found"))
    drift_flag = "drift detected & purged" if removed_banned else "input clean"
    checks.append(("Drift interception report", True, drift_flag))
    passed = all(c[1] for c in checks)
    return checks, ("PASS" if passed else "FAIL")

def process_brief(raw, anchor, vector_key, asset_type, platform, aspect, kelvin):
    step1, filler_hits = purge_filler(raw, anchor)
    step2, banned_hits = purge_banned(step1, anchor)
    prompt, negatives, locks = lock_parameters(step2, anchor, vector_key, asset_type, platform, aspect, kelvin)
    checks, status = validate(step2, prompt, anchor, banned_hits, asset_type)
    vectors = anchor.get("vectors", DEFAULT_ANCHOR["vectors"])
    vec_title = vectors.get(vector_key, {}).get("title", vector_key)
    payload = {
        "xxlabs_bta_version": anchor.get("governance_version", "CIAT25.1"),
        "anchor_id": anchor.get("anchor_id", "BTA-XXL.01"),
        "anchor_hash": anchor_hash(anchor),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "asset_intent": step2,
        "asset_type": asset_type,
        "platform": platform,
        "brand_parameters": {
            "tone": anchor.get("tone", ""),
            "visual_vector": vec_title,
            "kelvin_lighting": f"{locks['kelvin_locked']}K (locked {anchor.get('kelvin_range', {}).get('min', 3200)}–{anchor.get('kelvin_range', {}).get('max', 5600)})",
            "color_channels": [c["name"] for c in anchor.get("color_channels", {}).get("active", [])],
            "forbidden_elements": anchor.get("forbidden_elements", [])
        },
        "execution_payload": {
            "prompt_string": prompt,
            "negative_prompt": negatives,
            "validation_status": status
        },
        "governance_telemetry": {
            "filler_purged": filler_hits,
            "banned_purged": banned_hits,
            "checks": [{"name": n, "passed": p, "detail": d} for n, p, d in checks]
        }
    }
    return payload, status

# ============================================================
# SESSION STATE
# ============================================================
if "anchor" not in st.session_state:
    st.session_state.anchor = normalize_anchor(DEFAULT_ANCHOR)
if "stats" not in st.session_state:
    st.session_state.stats = {"briefs": 0, "filler_purged": 0, "banned_purged": 0, "fails": 0}
if "history" not in st.session_state:
    st.session_state.history = []

anchor = normalize_anchor(st.session_state.anchor)
current_hash = anchor_hash(anchor)

# ============================================================
# SIDEBAR — LIVE TELEMETRY
# ============================================================
with st.sidebar:
    st.title("⬡ XX_LABS")
    st.caption("Deterministic Brand Governance — CIAT25.1")
    st.divider()
    st.markdown(f"**Anchor:** {anchor.get('anchor_name', 'N/A')}")
    st.markdown(f"**ID:** `{anchor.get('anchor_id', 'N/A')}`")
    st.markdown(f"**Hash:** `{current_hash}`")
    st.markdown(f"**Version:** {anchor.get('governance_version','—')}")
    st.divider()
    st.markdown("**Locked color channels**")
    for c in anchor.get("color_channels", {}).get("active", []):
        st.markdown(
            f'<span style="display:inline-block;width:14px;height:14px;'
            f'background:{c.get("hex", "#000")};border-radius:3px;margin-right:6px;"></span>'
            f'{c.get("name", "")} (`{c.get("hex", "")}`)',
            unsafe_allow_html=True
        )
    kr = anchor.get("kelvin_range", {"min": 3200, "max": 5600})
    st.markdown(f"**Kelvin lock:** {kr.get('min', 3200)}K – {kr.get('max', 5600)}K")
    st.markdown(f"**Default AR:** {anchor.get('default_aspect','16:9')}")
    st.divider()
    st.markdown("**Session telemetry**")
    s = st.session_state.stats
    st.metric("Briefs governed", s["briefs"])
    st.metric("Filler terms purged", s["filler_purged"])
    st.metric("Banned tokens purged", s["banned_purged"])
    st.metric("FAIL verdicts", s["fails"])
    st.divider()
    up = st.file_uploader("Load brand_anchor.json", type=["json"])
    if up is not None:
        try:
            content = up.read().decode("utf-8")
            raw_json = json.loads(content)
            st.session_state.anchor = normalize_anchor(raw_json)
            st.success("Anchor loaded & synchronized.")
            st.rerun()
        except Exception as e:
            st.error(f"Invalid anchor file: {e}")

# ============================================================
# MAIN
# ============================================================
st.title("XX_LABS — BTA Workbench")
st.caption("Ambiguity is stripped. Parameters are locked. Verification runs on the prompt, not the pixels.")

tab1, tab2 = st.tabs(["① Forge / Edit Anchor", "② Govern a Brief"])

# ---------------- TAB 1: ANCHOR BUILDER ----------------
with tab1:
    st.subheader("Anchor Interview — forge a Brand Truth Anchor")
    st.caption("The anchor is the product. Everything downstream is enforcement.")
    
    vecs = anchor.get("vectors", DEFAULT_ANCHOR["vectors"])
    alpha_v = vecs.get("alpha", {})
    beta_v = vecs.get("beta", {})
    active_cols_str = "\n".join(f"{c['name']},{c['hex']}" for c in anchor.get("color_channels", {}).get("active", []))
    forbidden_cols_str = ", ".join(anchor.get("color_channels", {}).get("forbidden", []))
    mats_str = "\n".join(anchor.get("materials", []))
    geo_str = "\n".join(anchor.get("geometry_overlays", []))
    comp_str = ", ".join(anchor.get("competitor_names", []))

    with st.form(f"anchor_form_{current_hash}"):
        c1, c2 = st.columns(2)
        a_name = c1.text_input("Anchor name", anchor.get("anchor_name", ""))
        a_tone = c2.text_input("Locked tone", anchor.get("tone", ""))
        st.markdown("**Style vectors**")
        v1t = st.text_input("Vector Alpha title", alpha_v.get("title", ""))
        v1d = st.text_area("Vector Alpha description", alpha_v.get("description", ""), height=100)
        v2t = st.text_input("Vector Beta title", beta_v.get("title", ""))
        v2d = st.text_area("Vector Beta description", beta_v.get("description", ""), height=80)
        st.markdown("**Color channels** (name,hex — one per line)")
        active_lines = st.text_area("Active (locked) channels", active_cols_str, height=90)
        forbidden_cols = st.text_area("Forbidden channels (comma-separated)", forbidden_cols_str, height=60)
        kr1, kr2, ar = st.columns(3)
        k_min = kr1.number_input("Kelvin min", 1000, 10000, int(anchor.get("kelvin_range", {}).get("min", 3200)))
        k_max = kr2.number_input("Kelvin max", 1000, 10000, int(anchor.get("kelvin_range", {}).get("max", 5600)))
        a_ar = ar.text_input("Default aspect ratio", anchor.get("default_aspect", "16:9"))
        a_mats = st.text_area("Materials (one per line)", mats_str, height=70)
        a_geo = st.text_area("Geometry overlays (one per line)", geo_str, height=60)
        a_comp = st.text_input("Competitor names to purge (comma-separated)", comp_str)
        submitted = st.form_submit_button("Forge Anchor → compute hash")

    if submitted:
        def _lines(s): return [x.strip() for x in s.split("\n") if x.strip()]
        def _csv(s): return [x.strip() for x in s.split(",") if x.strip()]
        cols = []
        for ln in _lines(active_lines):
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) == 2:
                cols.append({"name": parts[0], "hex": parts[1]})
        new_anchor = {
            "anchor_id": anchor.get("anchor_id", "BTA-XXL.01"),
            "anchor_name": a_name,
            "governance_version": anchor.get("governance_version", "CIAT25.1"),
            "tone": a_tone,
            "vectors": {
                "alpha": {"title": v1t, "description": v1d},
                "beta": {"title": v2t, "description": v2d}
            },
            "color_channels": {"active": cols, "forbidden": _csv(forbidden_cols)},
            "kelvin_range": {"min": int(k_min), "max": int(k_max)},
            "materials": _lines(a_mats),
            "geometry_overlays": _lines(a_geo),
            "filler_phrases": anchor.get("filler_phrases", DEFAULT_ANCHOR["filler_phrases"]),
            "forbidden_elements": anchor.get("forbidden_elements", []),
            "competitor_names": _csv(a_comp),
            "default_aspect": a_ar
        }
        st.session_state.anchor = normalize_anchor(new_anchor)
        st.success(f"Anchor forged. Hash: `{anchor_hash(st.session_state.anchor)}`")
        st.rerun()

# ---------------- TAB 2: BRIEF GOVERNOR ----------------
with tab2:
    st.subheader("Drift Interception — paste a messy brief")
    vectors = anchor.get("vectors", DEFAULT_ANCHOR["vectors"])
    vector_keys = list(vectors.keys())
    g1, g2, g3, g4 = st.columns(4)
    vector_sel = g1.selectbox("Style vector", vector_keys,
                              format_func=lambda k: vectors.get(k, {}).get("title", k))
    asset_sel = g2.selectbox("Asset type", ["still", "motion", "copy"])
    platform_sel = g3.selectbox("Target engine", ["Midjourney", "Runway", "Kling", "Universal"])
    ar_sel = g4.text_input("Aspect ratio", anchor.get("default_aspect", "16:9"))
    kr = anchor.get("kelvin_range", {"min": 3200, "max": 5600})
    kelvin_sel = st.slider("Lighting temperature (locked range)", 2000, 6500,
                           int((kr.get("min", 3200) + kr.get("max", 5600)) / 2))
    raw = st.text_area("Raw brief", placeholder="e.g. make an awesome epic 8k render of a futuristic processor, laser blue glow, very cool, cyberpunk vibe…",
                       height=140)
    if st.button("Run Governance ⬡", type="primary") and raw.strip():
        payload, status = process_brief(raw, anchor, vector_sel, asset_sel, platform_sel, ar_sel, kelvin_sel)
        s = st.session_state.stats
        s["briefs"] += 1
        s["filler_purged"] += len(payload["governance_telemetry"]["filler_purged"])
        s["banned_purged"] += len(payload["governance_telemetry"]["banned_purged"])
        if status == "FAIL":
            s["fails"] += 1
        st.session_state.history.append(payload)

        if status == "PASS":
            st.success("VALIDATION: **PASS** — all lexical gates green.")
        else:
            st.error("VALIDATION: **FAIL** — see failing checks below.")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**[Cleaned Asset Brief]**")
            st.write(payload["asset_intent"] or "*(empty — blocked)*")
            tel = payload["governance_telemetry"]
            if tel["filler_purged"]:
                st.caption("Filler purged: " + ", ".join(f"`{t}`" for t in tel["filler_purged"]))
            if tel["banned_purged"]:
                st.caption("🚫 Drift purged: " + ", ".join(f"`{t}`" for t in tel["banned_purged"]))
            st.markdown("**Locked execution prompt**")
            st.code(payload["execution_payload"]["prompt_string"], language="text")
        with m2:
            st.markdown("**Gate checks**")
            for name, passed, detail in [(c["name"], c["passed"], c["detail"]) for c in tel["checks"]]:
                st.markdown(f"{'✅' if passed else '❌'} **{name}** — {detail}")
            st.download_button("Download execution payload (.json)",
                               json.dumps(payload, indent=2, ensure_ascii=False),
                               f"xxlabs_payload_{payload['anchor_hash'].replace(':','')}.json",
                               "application/json")

    if st.session_state.history:
        with st.expander(f"Session history ({len(st.session_state.history)} governed)"):
            for i, h in enumerate(reversed(st.session_state.history[-10:]), 1):
                st.caption(f"{i}. [{h['timestamp_utc'][11:19]}] {h['asset_type']}/{h['platform']} → "
                           f"**{h['execution_payload']['validation_status']}** | intent: {h['asset_intent'][:60]}…")

st.divider()
st.caption("XX_LABS BTA Workbench — verification on the prompt, not the pixels.")
