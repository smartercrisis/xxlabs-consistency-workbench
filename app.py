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

def load_and_merge_json(raw: dict) -> dict:
    if not isinstance(raw, dict):
        return DEFAULT_ANCHOR.copy()
    
    # Handle bta_master_registry schema
    reg = raw.get("bta_master_registry")
    if reg and isinstance(reg, dict):
        merged = DEFAULT_ANCHOR.copy()
        merged["anchor_id"] = "BTA-REGISTRY.01"
        merged["anchor_name"] = "BTA Master Registry"
        merged["governance_version"] = "CIAT25.1"
        
        vis_vectors = reg.get("visual_content_governance_and_style_vectors", [])
        if isinstance(vis_vectors, list) and len(vis_vectors) > 0:
            vectors_dict = {}
            for i, vec in enumerate(vis_vectors):
                key = "alpha" if i == 0 else ("beta" if i == 1 else f"vector_{i+1}")
                title = vec.get("name", f"Vector {i+1}")
                desc = f"{vec.get('visual_parameters', '')} Color discipline: {vec.get('color_discipline', '')}"
                vectors_dict[key] = {"title": title, "description": desc}
            merged["vectors"] = vectors_dict
            
        merged["color_channels"] = {
            "active": [
                {"name": "crimson red", "hex": "#DC143C"},
                {"name": "nature green", "hex": "#00FF7F"},
                {"name": "royal gold", "hex": "#D4AF37"}
            ],
            "forbidden": ["laser blue", "generic blue glow", "electric blue", "cyan glow"]
        }
        return merged

    # Fallback to standard schema
    merged = DEFAULT_ANCHOR.copy()
    merged["anchor_id"] = raw.get("anchor_id") or raw.get("id") or merged["anchor_id"]
    merged["anchor_name"] = raw.get("anchor_name") or raw.get("name") or raw.get("title") or merged["anchor_name"]
    merged["governance_version"] = raw.get("governance_version") or raw.get("version") or merged["governance_version"]
    merged["tone"] = raw.get("tone") or raw.get("brand_tone") or merged["tone"]
    
    vecs = raw.get("vectors") or raw.get("style_vectors")
    if isinstance(vecs, dict) and vecs:
        merged["vectors"] = vecs
        
    cc = raw.get("color_channels") or raw.get("colors")
    if isinstance(cc, dict):
        merged["color_channels"] = cc
    elif isinstance(cc, list):
        merged["color_channels"] = {"active": cc, "forbidden": raw.get("forbidden_colors", [])}
        
    kr = raw.get("kelvin_range") or raw.get("kelvin")
    if isinstance(kr, dict):
        merged["kelvin_range"] = kr
        
    for k in ["materials", "geometry_overlays", "filler_phrases", "forbidden_elements", "competitor_names"]:
        if k in raw and isinstance(raw[k], list):
            merged[k] = raw[k]
            
    if "default_aspect" in raw:
        merged["default_aspect"] = raw["default_aspect"]
    elif "aspect_ratio" in raw:
        merged["default_aspect"] = raw["aspect_ratio"]
        
    return merged

# ============================================================
# DETERMINISTIC CORE
# ============================================================
def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)

def anchor_hash(anchor: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(anchor).encode("utf-8")).hexdigest()[:12]

def purge_filler(text: str, anchor: dict):
    removed, cleaned = [], text
    phrases = anchor.get("filler_phrases", [])
    if not isinstance(phrases, list):
        phrases = []
    for phrase in sorted(phrases, key=len, reverse=True):
        if not phrase:
            continue
        escaped_term = re.escape(str(phrase).strip())
        pattern = re.compile(r"\b" + escaped_term + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            removed.append(phrase)
            cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;."), removed

def purge_banned(text: str, anchor: dict):
    cc = anchor.get("color_channels", {})
    forbidden = cc.get("forbidden", []) if isinstance(cc, dict) else []
    comps = anchor.get("competitor_names", [])
    banned = list(forbidden) + list(comps)
    removed, cleaned = [], text
    for term in sorted([b for b in banned if b and str(b).strip()], key=len, reverse=True):
        escaped_term = re.escape(str(term).strip())
        pattern = re.compile(r"\b" + escaped_term + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            removed.append(term)
            cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;."), removed

def lock_parameters(intent: str, anchor: dict, vector_key: str, asset_type: str,
                    platform: str, aspect: str, kelvin: int):
    vectors = anchor.get("vectors", DEFAULT_ANCHOR["vectors"])
    vec = vectors.get(vector_key, list(vectors.values())[0])
    
    active_cols = anchor.get("color_channels", {}).get("active", [])
    colors = ", ".join(c.get("name", "") for c in active_cols if isinstance(c, dict))
    hexes = ", ".join(c.get("hex", "") for c in active_cols if isinstance(c, dict))
    
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
        active = [c.get("name", "") for c in anchor.get("color_channels", {}).get("active", []) if isinstance(c, dict) and c.get("name", "").lower() in body]
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
    
    active_cols = [c.get("name") for c in anchor.get("color_channels", {}).get("active", []) if isinstance(c, dict)]
    
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
            "color_channels": active_cols,
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
# SESSION STATE MANAGEMENT
# ============================================================
if "anchor" not in st.session_state:
    st.session_state.anchor = DEFAULT_ANCHOR.copy()

if "stats" not in st.session_state:
    st.session_state.stats = {"briefs": 0, "filler_purged": 0, "banned_purged": 0, "fails": 0}

if "history" not in st.session_state:
    st.session_state.history = []

anchor = st.session_state.anchor
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
        if isinstance(c, dict):
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
            st.session_state.anchor = load_and_merge_json(raw_json)
            st.success("Anchor file loaded and synced.")
            st.rerun()
        except Exception as e:
            st.error(f"Invalid JSON file: {e}")

# ============================================================
# MAIN INTERFACE
# ============================================================
st.title("XX_LABS — BTA Workbench")
st.caption("Ambiguity is stripped. Parameters are locked. Verification runs on the prompt, not the pixels.")

tab1, tab2 = st.tabs(["① Forge / Edit Anchor", "② Govern a Brief"])

# ---------------- TAB 1: ANCHOR BUILDER (DYNAMIC VALUES, NO CACHED KEYS) ----------------
with tab1:
    st.subheader("Anchor Interview — forge a Brand Truth Anchor")
    st.caption("The anchor is the product. Everything downstream is enforcement.")
    
    vecs = anchor.get("vectors", {})
    vector_keys = list(vecs.keys())
    
    v_alpha_key = vector_keys[0] if len(vector_keys) > 0 else "alpha"
    v_beta_key = vector_keys[1] if len(vector_keys) > 1 else "beta"
    
    alpha_v = vecs.get(v_alpha_key, {})
    beta_v = vecs.get(v_beta_key, {})
    
    active_cols_list = anchor.get("color_channels", {}).get("active", [])
    active_cols_str = "\n".join(f"{c['name']},{c['hex']}" for c in active_cols_list if isinstance(c, dict) and "name" in c and "hex" in c)
    forbidden_cols_str = ", ".join(anchor.get("color_channels", {}).get("forbidden", []))
    
    mats_str = "\n".join(anchor.get("materials", []))
    geo_str = "\n".join(anchor.get("geometry_overlays", []))
    comp_str = ", ".join(anchor.get("competitor_names", []))

    # Without keys, these widgets bind directly to anchor data on every rerun
    c1, c2 = st.columns(2)
    a_name = c1.text_input("Anchor name", value=anchor.get("anchor_name", ""))
    a_tone = c2.text_input("Locked tone", value=anchor.get("tone", ""))
    
    st.markdown("**Style vectors**")
    v1t = st.text_input(f"Vector ({v_alpha_key}) title", value=alpha_v.get("title", ""))
    v1d = st.text_area(f"Vector ({v_alpha_key}) description", value=alpha_v.get("description", ""), height=100)
    
    v2t = st.text_input(f"Vector ({v_beta_key}) title", value=beta_v.get("title", ""))
    v2d = st.text_area(f"Vector ({v_beta_key}) description", value=beta_v.get("description", ""), height=80)
    
    st.markdown("**Color channels** (name,hex — one per line)")
    active_lines = st.text_area("Active (locked) channels", value=active_cols_str, height=90)
    forbidden_cols = st.text_area("Forbidden channels (comma-separated)", value=forbidden_cols_str, height=60)
    
    kr = anchor.get("kelvin_range", {"min": 3200, "max": 5600})
    kr1, kr2, ar = st.columns(3)
    k_min = kr1.number_input("Kelvin min", 1000, 10000, value=int(kr.get("min", 3200)))
    k_max = kr2.number_input("Kelvin max", 1000, 10000, value=int(kr.get("max", 5600)))
    a_ar = ar.text_input("Default aspect ratio", value=anchor.get("default_aspect", "16:9"))
    
    a_mats = st.text_area("Materials (one per line)", value=mats_str, height=70)
    a_geo = st.text_area("Geometry overlays (one per line)", value=geo_str, height=60)
    a_comp = st.text_input("Competitor names to purge (comma-separated)", value=comp_str)
    
    if st.button("Forge Anchor → compute hash", type="primary"):
        def _lines(s): return [x.strip() for x in s.split("\n") if x.strip()]
        def _csv(s): return [x.strip() for x in s.split(",") if x.strip()]
        
        cols = []
        for ln in _lines(active_lines):
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) == 2:
                cols.append({"name": parts[0], "hex": parts[1]})
                
        new_anchor = {
            "anchor_id": anchor.get("anchor_id", "BTA-CUSTOM.01"),
            "anchor_name": a_name,
            "governance_version": anchor.get("governance_version", "CIAT25.1"),
            "tone": a_tone,
            "vectors": {
                v_alpha_key: {"title": v1t, "description": v1d},
                v_beta_key: {"title": v2t, "description": v2d}
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
        
        st.session_state.anchor = new_anchor
        st.success(f"Anchor forged. Hash: `{anchor_hash(new_anchor)}`")
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
    ar_sel = g4.text_input("Aspect ratio", value=anchor.get("default_aspect", "16:9"))
    
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
