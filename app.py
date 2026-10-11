import copy
import datetime
import hashlib
import json
import re
import streamlit as st

st.set_page_config(page_title="XX_LABS BTA Workbench", page_icon="⬡", layout="wide")

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

def new_default() -> dict:
    return copy.deepcopy(DEFAULT_ANCHOR)

def _vector_key(i: int) -> str:
    return {0: "alpha", 1: "beta", 2: "gamma"}.get(i, f"vector_{i+1}")

def load_and_merge_json(raw: dict):
    """Returns (anchor, format_label)."""
    if not isinstance(raw, dict):
        raise ValueError("Top-level JSON must be an object.")

    # Format 1: BTA Master Registry (wrapped)
    reg = raw.get("bta_master_registry")
    if isinstance(reg, dict):
        merged = new_default()
        merged["anchor_id"] = "BTA-REGISTRY.01"
        merged["anchor_name"] = "BTA Master Registry"
        vis = reg.get("visual_content_governance_and_style_vectors", [])
        if isinstance(vis, list) and vis:
            vectors = {}
            for i, vec in enumerate(vis):
                if not isinstance(vec, dict):
                    continue
                # color_discipline is NOT embedded: it contains forbidden terms
                # ("laser blue") that would trip the leak gate. Colors come from color_channels.
                vectors[_vector_key(i)] = {
                    "title": vec.get("name", f"Vector {i+1}"),
                    "description": vec.get("visual_parameters", "")
                }
            if vectors:
                merged["vectors"] = vectors
        merged["color_channels"] = {
            "active": [
                {"name": "crimson red", "hex": "#DC143C"},
                {"name": "nature green", "hex": "#00FF7F"},
                {"name": "royal gold", "hex": "#D4AF37"}
            ],
            "forbidden": ["laser blue", "neon blue", "generic blue glow", "electric blue", "cyan glow"]
        }
        return merged, "BTA Master Registry"

    # Format 2: native anchor schema
    merged = new_default()
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
        if isinstance(raw.get(k), list):
            merged[k] = raw[k]

    if "default_aspect" in raw:
        merged["default_aspect"] = raw["default_aspect"]
    elif "aspect_ratio" in raw:
        merged["default_aspect"] = raw["aspect_ratio"]

    return merged, "Native anchor schema"

def parse_uploaded_anchor_file(data: bytes):
    """Returns (anchor, format_label). Raises ValueError if nothing usable is found."""
    content = data.decode("utf-8-sig")  # strips BOM, which silently broke json.loads before
    try:
        return load_and_merge_json(json.loads(content))
    except json.JSONDecodeError:
        pass
    # Tolerate junk around the JSON object
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        try:
            return load_and_merge_json(json.loads(content[start:end + 1]))
        except json.JSONDecodeError:
            pass
    # key=value fallback
    merged, hits = new_default(), 0
    keymap = {"anchor_name": "anchor_name", "anchor_id": "anchor_id", "tone": "tone",
              "governance_version": "governance_version", "default_aspect": "default_aspect"}
    for line in content.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip().lower()
            if k in keymap:
                merged[keymap[k]] = v.strip()
                hits += 1
    if hits == 0:
        raise ValueError("File is not valid JSON and contains no recognised key=value lines.")
    return merged, "key=value fallback"

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
        pattern = re.compile(r"\b" + re.escape(str(phrase).strip()) + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            removed.append(phrase)
            cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;."), removed

def purge_banned(text: str, anchor: dict):
    cc = anchor.get("color_channels", {})
    forbidden = cc.get("forbidden", []) if isinstance(cc, dict) else []
    banned = list(forbidden) + list(anchor.get("competitor_names", []))
    removed, cleaned = [], text
    for term in sorted([b for b in banned if b and str(b).strip()], key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(str(term).strip()) + r"\b", re.IGNORECASE)
        if pattern.search(cleaned):
            removed.append(term)
            cleaned = pattern.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip(" ,;."), removed

def lock_parameters(intent, anchor, vector_key, asset_type, platform, aspect, kelvin):
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
        prompt = f"{base} --no {negatives} --ar {aspect}"
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

def validate(intent, prompt, anchor, removed_banned, asset_type="still"):
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
        active = [c.get("name", "") for c in anchor.get("color_channels", {}).get("active", [])
                  if isinstance(c, dict) and c.get("name", "").lower() in body]
        checks.append(("Approved color channel locked", len(active) >= 1, f"locked: {active}"))

        kr = anchor.get("kelvin_range", {})
        m = re.search(r"(\d{4})K", prompt)
        kelvin_ok = bool(m) and kr.get("min", 0) <= int(m.group(1)) <= kr.get("max", 9999)
        checks.append(("Kelvin within lock range", kelvin_ok,
                       f"{m.group(1)}K in {kr.get('min')}–{kr.get('max')}K" if m else "no Kelvin value found"))

    checks.append(("Drift interception report", True, "drift detected & purged" if removed_banned else "input clean"))
    return checks, ("PASS" if all(c[1] for c in checks) else "FAIL")

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

# ---------------- session state ----------------
if "anchor" not in st.session_state:
    st.session_state.anchor = new_default()
if "anchor_source" not in st.session_state:
    st.session_state.anchor_source = "built-in default"
if "last_upload" not in st.session_state:
    st.session_state.last_upload = None
if "uploader_nonce" not in st.session_state:
    st.session_state.uploader_nonce = 0
if "stats" not in st.session_state:
    st.session_state.stats = {"briefs": 0, "filler_purged": 0, "banned_purged": 0, "fails": 0}
if "history" not in st.session_state:
    st.session_state.history = []

# ---------------- upload handling (runs BEFORE anchor is read) ----------------
# Process each distinct file exactly once. The old code called st.rerun() on every
# run while the file was still in the uploader, so it looped and also overwrote forged edits.
with st.sidebar:
    up = st.file_uploader("Load brand anchor config (.txt / .json)", type=["txt", "json"],
                          key=f"uploader_{st.session_state.uploader_nonce}")
    if up is not None:
        data = up.getvalue()
        fid = hashlib.sha256(data).hexdigest()
        if st.session_state.last_upload != fid:
            try:
                new_anchor, fmt = parse_uploaded_anchor_file(data)
                st.session_state.anchor = new_anchor
                st.session_state.anchor_source = f"{up.name} ({fmt})"
                st.session_state.last_upload = fid
                st.rerun()
            except Exception as e:
                st.session_state.last_upload = fid  # do not retry a bad file in a loop
                st.error(f"Failed to load anchor: {e}")

anchor = st.session_state.anchor
current_hash = anchor_hash(anchor)

with st.sidebar:
    st.title("⬡ XX_LABS")
    st.caption("Deterministic Brand Governance — CIAT25.1")
    st.divider()
    st.markdown(f"**Anchor:** {anchor.get('anchor_name', 'N/A')}")
    st.markdown(f"**ID:** `{anchor.get('anchor_id', 'N/A')}`")
    st.markdown(f"**Hash:** `{current_hash}`")
    st.markdown(f"**Version:** {anchor.get('governance_version','—')}")
    st.markdown(f"**Source:** {st.session_state.anchor_source}")
    st.markdown(f"**Vectors:** {len(anchor.get('vectors', {}))}")
    if st.button("Reset to built-in default / re-enable upload"):
        st.session_state.anchor = new_default()
        st.session_state.anchor_source = "built-in default"
        st.session_state.last_upload = None
        st.session_state.uploader_nonce += 1
        st.rerun()
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

st.title("XX_LABS — BTA Workbench")
st.caption("Ambiguity is stripped. Parameters are locked. Verification runs on the prompt, not the pixels.")

tab1, tab2 = st.tabs(["① Forge / Edit Anchor", "② Govern a Brief"])

with tab1:
    st.subheader("Anchor Interview — forge a Brand Truth Anchor")
    st.caption("The anchor is the product. Everything downstream is enforcement.")

    vecs = anchor.get("vectors", {})
    active_cols_list = anchor.get("color_channels", {}).get("active", [])
    active_cols_str = "\n".join(f"{c['name']},{c['hex']}" for c in active_cols_list
                                if isinstance(c, dict) and "name" in c and "hex" in c)
    forbidden_cols_str = ", ".join(anchor.get("color_channels", {}).get("forbidden", []))
    mats_str = "\n".join(anchor.get("materials", []))
    geo_str = "\n".join(anchor.get("geometry_overlays", []))
    comp_str = ", ".join(anchor.get("competitor_names", []))

    c1, c2 = st.columns(2)
    a_name = c1.text_input("Anchor name", value=anchor.get("anchor_name", ""), key=f"name_{current_hash}")
    a_tone = c2.text_input("Locked tone", value=anchor.get("tone", ""), key=f"tone_{current_hash}")

    st.markdown("### Style Vectors (Dynamic Registry)")
    edited_vectors = {}
    for v_key, v_data in vecs.items():
        st.markdown(f"**Vector ID: `{v_key}`**")
        vt = st.text_input(f"Title ({v_key})", value=v_data.get("title", ""), key=f"v_title_{v_key}_{current_hash}")
        vd = st.text_area(f"Description ({v_key})", value=v_data.get("description", ""), height=90,
                          key=f"v_desc_{v_key}_{current_hash}")
        edited_vectors[v_key] = {"title": vt, "description": vd}
        st.divider()

    st.markdown("**Color channels** (name,hex — one per line)")
    active_lines = st.text_area("Active (locked) channels", value=active_cols_str, height=90, key=f"active_{current_hash}")
    forbidden_cols = st.text_area("Forbidden channels (comma-separated)", value=forbidden_cols_str, height=60,
                                  key=f"forbidden_{current_hash}")

    kr1, kr2, ar = st.columns(3)
    k_min = kr1.number_input("Kelvin min", 1000, 10000, value=int(anchor.get("kelvin_range", {}).get("min", 3200)), key=f"kmin_{current_hash}")
    k_max = kr2.number_input("Kelvin max", 1000, 10000, value=int(anchor.get("kelvin_range", {}).get("max", 5600)), key=f"kmax_{current_hash}")
    a_ar = ar.text_input("Default aspect ratio", value=anchor.get("default_aspect", "16:9"), key=f"ar_{current_hash}")

    a_mats = st.text_area("Materials (one per line)", value=mats_str, height=70, key=f"mats_{current_hash}")
    a_geo = st.text_area("Geometry overlays (one per line)", value=geo_str, height=60, key=f"geo_{current_hash}")
    a_comp = st.text_input("Competitor names to purge (comma-separated)", value=comp_str, key=f"comp_{current_hash}")

    cA, cB = st.columns(2)
    if cA.button("Forge Anchor → compute hash", type="primary"):
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
            "vectors": edited_vectors,
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
        st.session_state.anchor_source = "forged in UI"
        st.rerun()

    # Export lets the forged anchor round-trip back into an uploadable .txt
    cB.download_button("Export current anchor (.txt)",
                       json.dumps(anchor, indent=2, ensure_ascii=False),
                       f"{anchor.get('anchor_id','anchor')}.txt", "text/plain")

with tab2:
    st.subheader("Drift Interception — paste a messy brief")
    vectors = anchor.get("vectors", DEFAULT_ANCHOR["vectors"])
    vector_keys = list(vectors.keys())

    g1, g2, g3, g4 = st.columns(4)
    vector_sel = g1.selectbox("Style vector", vector_keys,
                              format_func=lambda k: vectors.get(k, {}).get("title", k))
    asset_sel = g2.selectbox("Asset type", ["still", "motion", "copy"])
    platform_sel = g3.selectbox("Target engine", ["Midjourney", "Runway", "Kling", "Universal"])
    ar_sel = g4.text_input("Aspect ratio", value=anchor.get("default_aspect", "16:9"), key=f"ar_sel_{current_hash}")

    kr = anchor.get("kelvin_range", {"min": 3200, "max": 5600})
    kelvin_sel = st.slider("Lighting temperature (locked range)", 2000, 6500,
                           int((kr.get("min", 3200) + kr.get("max", 5600)) / 2), key=f"kelvin_{current_hash}")

    raw = st.text_area("Raw brief",
                       placeholder="e.g. make an awesome epic 8k render of a futuristic processor, laser blue glow, very cool, cyberpunk vibe…",
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

        tel = payload["governance_telemetry"]
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**[Cleaned Asset Brief]**")
            st.write(payload["asset_intent"] or "*(empty — blocked)*")
            if tel["filler_purged"]:
                st.caption("Filler purged: " + ", ".join(f"`{t}`" for t in tel["filler_purged"]))
            if tel["banned_purged"]:
                st.caption("🚫 Drift purged: " + ", ".join(f"`{t}`" for t in tel["banned_purged"]))
            st.markdown("**Locked execution prompt**")
            st.code(payload["execution_payload"]["prompt_string"], language="text")
        with m2:
            st.markdown("**Gate checks**")
            for c in tel["checks"]:
                st.markdown(f"{'✅' if c['passed'] else '❌'} **{c['name']}** — {c['detail']}")
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
