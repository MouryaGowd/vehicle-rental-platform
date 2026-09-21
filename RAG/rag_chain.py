"""
RAG pipeline for JW Marriott Bengaluru hotel assistant.

Two modes (both 100% free):
  1. HuggingFace Inference API  — set HF_TOKEN or enter in sidebar
  2. Smart retrieval-only        — instant fallback when no token given
"""

import os
import re
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

CHROMA_DIR = "chroma_db"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 6
HF_MODEL = "google/flan-t5-base"

# Chroma's default distance is L2 over normalized embeddings, so smaller = closer.
# Anything with a best-match distance above this is treated as "not about the hotel".
# Calibrated against hotel_data.csv: real hotel questions score <= ~1.11
# ("Is there a spa?"), unrelated questions score >= ~1.59 ("who won the cricket
# match"). 1.35 sits in the gap. Re-check this if hotel_data.csv changes a lot.
OFF_TOPIC_MAX_DISTANCE = 1.35

OFF_TOPIC_MESSAGE = (
    "I'm the JW Marriott Bengaluru concierge assistant, so I can only help with "
    "questions about the hotel — rooms, dining, amenities, spa, events, location, "
    "or policies. Could you ask me something about your stay?"
)

_GREETING_RE = re.compile(
    r"^\s*(hi|hii+|hello+|hey+|good\s*(morning|afternoon|evening)|"
    r"thanks?|thank\s*you|thx|bye|goodbye|see\s*you)[\s!.,]*$",
    re.IGNORECASE,
)


def _is_greeting(question: str) -> bool:
    return bool(_GREETING_RE.match(question))


def _greeting_reply(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["thank", "thx"]):
        return "You're most welcome! Is there anything else I can help you with?"
    if any(w in q for w in ["bye", "goodbye", "see you"]):
        return "Thank you for choosing JW Marriott Bengaluru — have a wonderful day!"
    return (
        "Hello! 👋 I'm your JW Marriott Bengaluru concierge. "
        "Ask me about rooms, dining, amenities, spa, events, or hotel policies."
    )


FOLLOWUPS = {
    "suite":    "Would you like to reserve a suite, or shall I compare options for you?",
    "room":     "Would you like to book this room, or shall I show you other room types?",
    "dining":   "Would you like to make a dining reservation or know more about the menu?",
    "spa":      "Would you like to book a spa treatment? I can check availability for you.",
    "pool":     "Is there anything else you'd like to know about our facilities?",
    "meeting":  "Would you like our events team to contact you about availability and setup?",
    "price":    "Would you like to check availability for specific dates?",
    "location": "Would you like me to arrange an airport transfer or cab?",
    "policy":   "Do you have any other questions about your upcoming stay?",
    "package":  "Would you like to reserve one of these packages or know what's included?",
    "default":  "Is there anything else I can help you with?",
}


# ── Intent detection ───────────────────────────────────────────────────────────

def _intent(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["price", "cost", "how much", "rate", "charge", "fee", "expensive"]):
        return "price"
    if any(w in q for w in ["suite", "presidential", "jw suite", "junior suite", "executive suite"]):
        return "suite"
    if any(w in q for w in ["room", "deluxe", "premier", "bed", "occupancy", "floor", "size"]):
        return "room"
    if any(w in q for w in ["restaurant", "food", "dining", "eat", "breakfast", "lunch", "dinner",
                             "spice kitchen", "ricks", "lounge", "menu", "cuisine"]):
        return "dining"
    if any(w in q for w in ["spa", "massage", "quan", "wellness", "treatment", "facial"]):
        return "spa"
    if any(w in q for w in ["pool", "swim", "gym", "fitness", "workout"]):
        return "pool"
    if any(w in q for w in ["meeting", "conference", "ballroom", "event", "wedding", "convention"]):
        return "meeting"
    if any(w in q for w in ["location", "address", "airport", "distance", "transport", "metro", "cab"]):
        return "location"
    if any(w in q for w in ["cancel", "policy", "check-in", "checkout", "pet", "smoking", "refund"]):
        return "policy"
    if any(w in q for w in ["package", "honeymoon", "deal", "offer"]):
        return "package"
    return "default"


# ── Content parser ─────────────────────────────────────────────────────────────

def _get(pattern: str, text: str, group: int = 1) -> str:
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(group).strip().rstrip('.') if m else ""


def _parse(content: str) -> dict:
    # Strip category prefix
    text = re.sub(r'^Category:\s*[\w\s]+\.\s*', '', content).strip()

    desc_match = re.match(r'^(.*?\.)\s', text)
    desc = desc_match.group(1) if desc_match else ""

    amenities_raw = _get(r'Amenities?\s+include[:\s]+(.*?)\.?\s*$', text)
    amenities = [a.strip() for a in re.split(r',\s*(?:and\s*)?', amenities_raw) if a.strip()] if amenities_raw else []

    specialties_raw = _get(r'Specialty(?:\s*dishes?)?\s*(?:include)?[:\s]+(.*?)(?:\.|Average)', text)
    specialties = [s.strip() for s in re.split(r',\s*(?:and\s*)?', specialties_raw) if s.strip()] if specialties_raw else []

    services_raw = _get(r'Services[:\s]+(.*?)(?:\.|Multilingual|Available|$)', text)
    services = [s.strip() for s in re.split(r',\s*(?:and\s*)?', services_raw) if s.strip()] if services_raw else []

    inclusions_raw = _get(r'Inclusions?[:\s]+(.*?)(?:Starting price|$)', text)
    inclusions = [i.strip() for i in re.split(r',\s*(?:and\s*)?', inclusions_raw) if i.strip()] if inclusions_raw else []

    return {
        "description": desc,
        "price":       _get(r'(?:Price|Starting price)[:\s]+(Rs\s*[\d,]+(?:\s*per\s*(?:night|person))?)', text),
        "size":        _get(r'Size[:\s]+([\d,]+\s*sq\s*ft)', text),
        "floor":       _get(r'Floor[:\s]+([^\.\,]+)', text),
        "bed":         _get(r'Bed(?:\s*options?|type)?[:\s]+([^\.\,]+)', text),
        "max_occ":     _get(r'Max\s*occupancy[:\s]+([^\.\,]+)', text),
        "view":        _get(r'View[:\s]+([^\.\,]+)', text),
        "hours":       _get(r'Hours[:\s]+([^\.\,]+)', text),
        "cuisine":     _get(r'Cuisine[:\s]+([^\.\,]+)', text),
        "capacity":    _get(r'Capacity[:\s]+([^\.\,]+)', text),
        "avg_cost":    _get(r'Average\s*cost[:\s]+(Rs\s*[\d,]+(?:\s*per\s*\w+)?)', text),
        "dress_code":  _get(r'Dress\s*code[:\s]+([^\.\,]+)', text),
        "amenities":   amenities,
        "specialties": specialties,
        "services":    services,
        "inclusions":  inclusions,
    }


# ── Structured formatters ──────────────────────────────────────────────────────

def _bullets(items: list[str], limit: int = 12) -> str:
    return "\n".join(f"- {i}" for i in items[:limit])


def _table_row(icon: str, label: str, value: str) -> str:
    return f"| {icon} **{label}** | {value} |"


def _format_room(name: str, d: dict) -> str:
    rows = []
    if d["price"]:    rows.append(_table_row("💰", "Price",        d["price"]))
    if d["size"]:     rows.append(_table_row("📐", "Size",         d["size"]))
    if d["floor"]:    rows.append(_table_row("🏢", "Floor",        d["floor"]))
    if d["bed"]:      rows.append(_table_row("🛏️", "Bed",          d["bed"]))
    if d["max_occ"]:  rows.append(_table_row("👥", "Max Guests",   d["max_occ"]))
    if d["view"]:     rows.append(_table_row("🌆", "View",         d["view"]))

    out = f"### 🛏️ {name}\n\n"
    if d["description"]:
        out += f"*{d['description']}*\n\n"
    if rows:
        out += "| | |\n|---|---|\n" + "\n".join(rows) + "\n"
    if d["amenities"]:
        out += f"\n**Amenities**\n{_bullets(d['amenities'])}\n"
    return out


def _format_dining(name: str, d: dict) -> str:
    rows = []
    if d["cuisine"]:    rows.append(_table_row("🍽️", "Cuisine",    d["cuisine"]))
    if d["hours"]:      rows.append(_table_row("🕐", "Hours",      d["hours"]))
    if d["capacity"]:   rows.append(_table_row("👥", "Capacity",   d["capacity"]))
    if d["avg_cost"]:   rows.append(_table_row("💰", "Avg Cost",   d["avg_cost"]))
    if d["dress_code"]: rows.append(_table_row("👔", "Dress Code", d["dress_code"]))

    out = f"### 🍽️ {name}\n\n"
    if d["description"]:
        out += f"*{d['description']}*\n\n"
    if rows:
        out += "| | |\n|---|---|\n" + "\n".join(rows) + "\n"
    if d["specialties"]:
        out += f"\n**Specialties**\n{_bullets(d['specialties'])}\n"
    return out


def _format_amenity(name: str, d: dict) -> str:
    rows = []
    if d["hours"]:    rows.append(_table_row("🕐", "Hours",    d["hours"]))
    if d["price"]:    rows.append(_table_row("💰", "Cost",     d["price"]))
    if d["capacity"]: rows.append(_table_row("👥", "Capacity", d["capacity"]))

    out = f"### ✨ {name}\n\n"
    if d["description"]:
        out += f"*{d['description']}*\n\n"
    if rows:
        out += "| | |\n|---|---|\n" + "\n".join(rows) + "\n"
    if d["services"]:
        out += f"\n**Services**\n{_bullets(d['services'])}\n"
    if d["amenities"]:
        out += f"\n**Facilities**\n{_bullets(d['amenities'])}\n"
    return out


def _format_package(name: str, d: dict) -> str:
    out = f"### 🎁 {name}\n\n"
    if d["description"]:
        out += f"*{d['description']}*\n\n"
    if d["price"]:
        out += f"💰 **Starting at {d['price']}**\n\n"
    if d["inclusions"]:
        out += f"**What's included**\n{_bullets(d['inclusions'])}\n"
    return out


def _format_generic(name: str, category: str, d: dict, content: str) -> str:
    # Strip category prefix and return clean bullet-friendly content
    text = re.sub(r'^Category:\s*[\w\s]+\.\s*', '', content).strip()
    # Turn ". " separated facts into bullets
    sentences = [s.strip() for s in re.split(r'\.\s+', text) if s.strip()]
    if len(sentences) <= 1:
        return f"### {name}\n\n{text}\n"
    out = f"### {name}\n\n*{sentences[0]}*\n\n"
    for s in sentences[1:]:
        out += f"- {s}\n"
    return out


def _format_doc(doc: Document) -> str:
    name = doc.metadata.get("name", "")
    category = doc.metadata.get("category", "").lower()
    content = doc.page_content
    d = _parse(content)

    if category == "room":
        return _format_room(name, d)
    if category == "dining":
        return _format_dining(name, d)
    if category in ("amenity",):
        return _format_amenity(name, d)
    if category == "package":
        return _format_package(name, d)
    return _format_generic(name, category, d, content)


# ── Price summary table ────────────────────────────────────────────────────────

def _price_summary(docs: list[Document]) -> str:
    rows = []
    for doc in docs:
        name = doc.metadata.get("name", "")
        d = _parse(doc.page_content)
        price = d["price"]
        size = d["size"]
        if price:
            row = f"| **{name}** | {price} |"
            if size:
                row = f"| **{name}** | {price} | {size} |"
            rows.append((name, price, size, row))

    if not rows:
        return ""

    has_size = any(r[2] for r in rows)
    if has_size:
        header = "| Option | Price | Size |\n|---|---|---|"
    else:
        header = "| Option | Price |\n|---|---|"
    return header + "\n" + "\n".join(r[3] for r in rows)


# ── Main smart answer ──────────────────────────────────────────────────────────

def _smart_answer(question: str, docs: list[Document]) -> str:
    if not docs:
        return "I'm sorry, I don't have that information. Could you ask something else about the hotel?"

    intent_ = _intent(question)
    followup = FOLLOWUPS.get(intent_, FOLLOWUPS["default"])
    divider = "\n\n---\n\n"

    # Price question — show a summary table then best match detail
    if intent_ == "price":
        table = _price_summary(docs)
        best_block = _format_doc(docs[0])
        if table:
            return f"### 💰 Pricing Overview\n\n{table}\n\n{best_block}{divider}💬 *{followup}*"
        return f"{best_block}{divider}💬 *{followup}*"

    # Suite question — list all suites with prices, then detail the best match
    if intent_ == "suite":
        suite_docs = [d for d in docs if "suite" in d.metadata.get("name", "").lower()]
        if suite_docs:
            table = _price_summary(suite_docs)
            best_block = _format_doc(suite_docs[0])
            header = "### 🏨 Our Suite Options\n\n"
            return f"{header}{table}\n\n{best_block}{divider}💬 *{followup}*"

    # Single best match with full structured layout
    return f"{_format_doc(docs[0])}{divider}💬 *{followup}*"


# ── HuggingFace Inference API ──────────────────────────────────────────────────

def _hf_api_answer(question: str, docs: list[Document], hf_token: str) -> str:
    from huggingface_hub import InferenceClient

    context = "\n\n".join(
        f"[{d.metadata.get('name', '')}]\n{d.page_content}" for d in docs
    )
    prompt = (
        "You are a professional hotel concierge at JW Marriott Bengaluru. "
        "Answer the guest's question using ONLY the hotel information below. "
        "Structure your reply clearly: lead with the direct answer, "
        "use bullet points for lists, and end with one helpful follow-up question.\n\n"
        f"Hotel information:\n{context}\n\n"
        f"Guest question: {question}\n\nConcierge answer:"
    )

    client = InferenceClient(token=hf_token)
    result = client.text_generation(prompt, model=HF_MODEL, max_new_tokens=400, temperature=0.3)
    return result.strip()


# ── RAG class ──────────────────────────────────────────────────────────────────

def _build_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


class HotelRAG:
    def __init__(self):
        self._embeddings = _build_embeddings()
        self._vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=self._embeddings,
        )

    def ask(self, question: str, hf_token: str = "") -> tuple[str, list[Document]]:
        if _is_greeting(question):
            return _greeting_reply(question), []

        scored = self._vectorstore.similarity_search_with_score(question, k=TOP_K)
        if not scored:
            return OFF_TOPIC_MESSAGE, []

        best_score = min(score for _, score in scored)
        if best_score > OFF_TOPIC_MAX_DISTANCE:
            return OFF_TOPIC_MESSAGE, []

        docs = [doc for doc, _ in scored]
        token = hf_token or os.getenv("HF_TOKEN", "")

        if token:
            try:
                answer = _hf_api_answer(question, docs, token)
            except Exception:
                answer = _smart_answer(question, docs)
                answer += "\n\n*(HF API unavailable right now — showing smart retrieval answer instead.)*"
        else:
            answer = _smart_answer(question, docs)

        return answer, docs
