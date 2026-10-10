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
    """Recursively merges uploaded JSON directly over defaults without losing explicit values."""
    if not isinstance(raw, dict):
        return DEFAULT_ANCHOR.copy()
    
    merged = DEFAULT_ANCHOR.copy()
    
    # Direct field mapping
    merged["anchor_id"] = raw.get("anchor_id") or raw.get("id") or merged["anchor_id"]
    merged["anchor_name"] = raw.get("anchor_name") or raw.get("name") or raw.get("title") or merged["anchor_name"]
    merged["governance_version"] = raw.get("governance_version") or raw.get("version") or merged["governance_version"]
    merged["tone"] = raw.get("tone") or raw.get("brand_tone") or merged["tone"]
    
    # Style vectors
    vecs = raw.get("vectors") or raw.get("style_vectors")
    if isinstance(vecs, dict) and vecs:
        merged["vectors"] = vecs
        
    # Color channels
    cc = raw.get("color_channels") or raw.get("colors")
    if isinstance(cc, dict):
        merged["color_channels"] = cc
    elif isinstance(cc, list):
        merged["color_channels"] = {"active": cc, "forbidden": raw.get("forbidden_colors", [])}
        
    # Kelvin range
    kr = raw.get("kelvin_range") or raw.get("kelvin")
    if isinstance(kr, dict):
        merged["kelvin_range"] = kr
        
    # Lists
    for k in ["materials", "geometry_overlays", "filler_phrases", "forbidden_elements", "competitor_names"]:
        if k in raw and isinstance(raw[k], list):
            merged[k] = raw[k]
            
    # Aspect ratio
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
        pattern = re.compile(r"\b" + _phrase_escape(term)
