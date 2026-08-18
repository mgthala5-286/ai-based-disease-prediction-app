from __future__ import annotations

import json
import os
import re
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, make_response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "_portal_data"
USERS_FILE = DATA_DIR / "users.json"
REPORTS_FILE = DATA_DIR / "reports.json"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "mediscope-dev-key")

SYMPTOMS = [
    {"id": "fever", "label": "Fever", "cat": "General", "keys": ["fever", "temperature", "high temperature"]},
    {"id": "chills", "label": "Chills", "cat": "General", "keys": ["chills", "shivering"]},
    {"id": "fatigue", "label": "Fatigue", "cat": "General", "keys": ["fatigue", "tired", "low energy"]},
    {"id": "body_ache", "label": "Body Ache", "cat": "General", "keys": ["body ache", "body pain", "muscle pain"]},
    {"id": "headache", "label": "Headache", "cat": "Neuro", "keys": ["headache", "head pain"]},
    {"id": "dizziness", "label": "Dizziness", "cat": "Neuro", "keys": ["dizzy", "dizziness", "lightheaded"]},
    {"id": "light_sensitivity", "label": "Light Sensitivity", "cat": "Neuro", "keys": ["light sensitivity", "photophobia"]},
    {"id": "cough", "label": "Cough", "cat": "Respiratory", "keys": ["cough", "coughing"]},
    {"id": "sore_throat", "label": "Sore Throat", "cat": "Respiratory", "keys": ["sore throat", "throat pain"]},
    {"id": "runny_nose", "label": "Runny Nose", "cat": "Respiratory", "keys": ["runny nose"]},
    {"id": "sneezing", "label": "Sneezing", "cat": "Respiratory", "keys": ["sneezing", "sneeze"]},
    {"id": "nasal_congestion", "label": "Nasal Congestion", "cat": "Respiratory", "keys": ["stuffy nose", "blocked nose", "nasal congestion"]},
    {"id": "loss_of_smell", "label": "Loss of Smell/Taste", "cat": "Respiratory", "keys": ["loss of smell", "loss of taste"]},
    {"id": "shortness_of_breath", "label": "Shortness of Breath", "cat": "Respiratory", "keys": ["shortness of breath", "breathing trouble", "breathless"]},
    {"id": "wheezing", "label": "Wheezing", "cat": "Respiratory", "keys": ["wheezing"]},
    {"id": "chest_pain", "label": "Chest Pain", "cat": "Warning", "keys": ["chest pain"]},
    {"id": "itchy_eyes", "label": "Itchy Eyes", "cat": "Allergy", "keys": ["itchy eyes", "watery eyes"]},
    {"id": "nausea", "label": "Nausea", "cat": "Digestive", "keys": ["nausea", "queasy"]},
    {"id": "vomiting", "label": "Vomiting", "cat": "Digestive", "keys": ["vomiting", "throwing up"]},
    {"id": "diarrhea", "label": "Diarrhea", "cat": "Digestive", "keys": ["diarrhea", "loose stool", "loose motion"]},
    {"id": "abdominal_pain", "label": "Abdominal Pain", "cat": "Digestive", "keys": ["abdominal pain", "stomach pain", "belly pain"]},
    {"id": "heartburn", "label": "Heartburn", "cat": "Digestive", "keys": ["heartburn", "acid reflux"]},
    {"id": "burning_urination", "label": "Burning Urination", "cat": "Urinary", "keys": ["burning urination", "pain while urinating"]},
    {"id": "frequent_urination", "label": "Frequent Urination", "cat": "Urinary", "keys": ["frequent urination", "urinating often"]},
    {"id": "excessive_thirst", "label": "Excessive Thirst", "cat": "Metabolic", "keys": ["excessive thirst", "very thirsty"]},
    {"id": "blurred_vision", "label": "Blurred Vision", "cat": "Metabolic", "keys": ["blurred vision", "blur vision"]},
    {"id": "dry_mouth", "label": "Dry Mouth", "cat": "Metabolic", "keys": ["dry mouth"]},
    {"id": "rash", "label": "Rash", "cat": "Skin", "keys": ["rash", "skin rash"]},
    {"id": "joint_pain", "label": "Joint Pain", "cat": "General", "keys": ["joint pain", "joint ache"]},
    {"id": "palpitations", "label": "Palpitations", "cat": "Cardio", "keys": ["palpitations", "heart racing", "fast heartbeat"]},
    {"id": "insomnia", "label": "Insomnia", "cat": "Sleep", "keys": ["insomnia", "trouble sleeping"]},
    {"id": "high_bp_reading", "label": "High BP Reading", "cat": "Cardio", "keys": ["high bp", "high blood pressure", "bp high"]},
    {"id": "swelling_feet", "label": "Swelling in Feet", "cat": "Kidney/Cardio", "keys": ["swollen feet", "leg swelling", "ankle swelling"]},
    {"id": "reduced_urine", "label": "Reduced Urine", "cat": "Kidney", "keys": ["less urine", "reduced urine", "low urine"]},
    {"id": "flank_pain", "label": "Flank or Back Pain", "cat": "Kidney", "keys": ["flank pain", "back pain", "side pain"]},
    {"id": "yellow_skin", "label": "Yellow Skin/Eyes", "cat": "Liver", "keys": ["yellow eyes", "yellow skin", "jaundice"]},
    {"id": "dark_urine", "label": "Dark Urine", "cat": "Liver/Urinary", "keys": ["dark urine", "tea colored urine"]},
    {"id": "appetite_loss", "label": "Appetite Loss", "cat": "General", "keys": ["loss of appetite", "appetite loss", "not hungry"]},
    {"id": "unexplained_weight_loss", "label": "Unexplained Weight Loss", "cat": "General", "keys": ["weight loss", "losing weight"]},
    {"id": "weight_gain", "label": "Weight Gain", "cat": "Metabolic", "keys": ["weight gain", "gaining weight"]},
    {"id": "tremor", "label": "Tremor", "cat": "Neuro", "keys": ["tremor", "shaking hands", "hand shaking"]},
    {"id": "slow_movement", "label": "Slow Movement", "cat": "Neuro", "keys": ["slow movement", "stiff movement", "body stiffness"]},
    {"id": "weakness_one_side", "label": "One-sided Weakness", "cat": "Warning", "keys": ["one sided weakness", "face droop", "arm weakness", "leg weakness"]},
    {"id": "slurred_speech", "label": "Slurred Speech", "cat": "Warning", "keys": ["slurred speech", "speech problem", "cannot speak clearly"]},
    {"id": "confusion", "label": "Confusion", "cat": "Warning", "keys": ["confusion", "confused", "disoriented"]},
    {"id": "neck_swelling", "label": "Neck Swelling", "cat": "Endocrine", "keys": ["neck swelling", "goiter", "thyroid swelling"]},
    {"id": "heat_intolerance", "label": "Heat Intolerance", "cat": "Endocrine", "keys": ["heat intolerance", "too hot", "sweating a lot"]},
    {"id": "cold_intolerance", "label": "Cold Intolerance", "cat": "Endocrine", "keys": ["cold intolerance", "feeling cold"]},
    {"id": "breast_lump", "label": "Breast Lump", "cat": "Warning", "keys": ["breast lump", "lump in breast"]},
    {"id": "nipple_discharge", "label": "Nipple Discharge", "cat": "Warning", "keys": ["nipple discharge", "blood from nipple"]},
    {"id": "coughing_blood", "label": "Coughing Blood", "cat": "Warning", "keys": ["coughing blood", "blood in sputum", "blood in cough"]},
    {"id": "night_sweats", "label": "Night Sweats", "cat": "General", "keys": ["night sweats", "sweating at night"]},
]

LOOKUP = {item["id"]: item for item in SYMPTOMS}
RED_FLAGS = {"chest_pain", "weakness_one_side", "slurred_speech", "confusion", "coughing_blood"}
CONDITIONS = []

CONDITIONS += [
    {
        "slug": "cold",
        "name": "Common Cold",
        "note": "A mild upper-respiratory viral pattern.",
        "sym": {"runny_nose": 4, "sneezing": 4, "sore_throat": 3, "nasal_congestion": 3, "cough": 2, "fatigue": 1, "fever": 1},
        "foods": ["Warm soup", "Honey with warm water", "Soft cooked meals", "Plain water"],
        "meds": ["Saline spray may help congestion.", "Paracetamol may help fever if safe for you.", "Throat lozenges can soothe irritation."],
        "steps": ["Rest and hydrate.", "Seek review if fever lasts more than 3 days or breathing worsens."],
    },
    {
        "slug": "flu",
        "name": "Influenza (Flu)",
        "note": "Flu often causes stronger fever, aches, and fatigue than a simple cold.",
        "sym": {"fever": 4, "chills": 3, "body_ache": 4, "fatigue": 4, "headache": 3, "cough": 3, "sore_throat": 2, "nausea": 1},
        "foods": ["Electrolyte drinks", "Rice porridge", "Banana", "Vegetable broth"],
        "meds": ["Paracetamol is often used for fever or body ache if it is safe for you.", "A clinician may discuss antivirals early in illness."],
        "steps": ["Rest and fluids matter.", "Get urgent help if breathing becomes difficult."],
    },
    {
        "slug": "covid",
        "name": "COVID-like Viral Illness",
        "note": "Smell loss with cough, fever, and fatigue fits a viral respiratory pattern.",
        "sym": {"fever": 4, "cough": 3, "fatigue": 3, "loss_of_smell": 5, "sore_throat": 2, "headache": 2, "shortness_of_breath": 4},
        "foods": ["Warm fluids", "Soup", "Fruit", "Light proteins"],
        "meds": ["Paracetamol can support fever relief if safe for you.", "Consider testing and medical review if symptoms are worsening."],
        "steps": ["Monitor breathing closely.", "Seek urgent care for chest pain or shortness of breath."],
    },
    {
        "slug": "allergy",
        "name": "Allergic Rhinitis",
        "note": "Sneezing, itchy eyes, and nasal symptoms often suggest allergy.",
        "sym": {"sneezing": 4, "itchy_eyes": 4, "runny_nose": 3, "nasal_congestion": 3, "cough": 1},
        "foods": ["Water", "Warm herbal tea", "Light anti-inflammatory meals"],
        "meds": ["A pharmacist may discuss a non-drowsy antihistamine.", "Saline rinse can help clear irritants."],
        "steps": ["Reduce dust, smoke, and pollen exposure if possible.", "Get reviewed if wheezing or breathing trouble appears."],
    },
    {
        "slug": "migraine",
        "name": "Migraine Pattern",
        "note": "Headache with nausea or light sensitivity can fit a migraine-style pattern.",
        "sym": {"headache": 5, "nausea": 2, "light_sensitivity": 4, "dizziness": 2},
        "foods": ["Water", "Regular light meals", "Magnesium-rich foods"],
        "meds": ["Paracetamol may help some headaches if safe for you.", "Repeated severe headaches need clinician review rather than repeat self-treatment."],
        "steps": ["Rest in a quiet dark room if possible.", "Seek urgent help for the worst headache of your life or weakness."],
    },
]

CONDITIONS += [
    {
        "slug": "gastritis",
        "name": "Acid Reflux or Gastritis",
        "note": "Burning after meals or upper-stomach discomfort often fits reflux or gastritis.",
        "sym": {"heartburn": 5, "abdominal_pain": 3, "nausea": 2, "vomiting": 1},
        "foods": ["Banana", "Oats", "Rice", "Non-spicy cooked vegetables"],
        "meds": ["A pharmacist may suggest a short-term antacid.", "Avoid ibuprofen-like painkillers if stomach irritation is possible."],
        "steps": ["Eat smaller meals.", "Seek care if pain is severe or vomiting repeats."],
    },
    {
        "slug": "gastroenteritis",
        "name": "Gastroenteritis or Food Poisoning",
        "note": "Vomiting or diarrhea with stomach pain commonly fits stomach infection or food poisoning.",
        "sym": {"diarrhea": 4, "vomiting": 3, "nausea": 3, "abdominal_pain": 3, "fever": 2, "dizziness": 1},
        "foods": ["ORS", "Banana", "Rice", "Toast"],
        "meds": ["ORS is important for fluid replacement.", "Avoid random antibiotics or antidiarrheal tablets if stool is bloody or fever is high."],
        "steps": ["Watch for dehydration signs.", "Urgent care is needed for fainting, blood in stool, or persistent vomiting."],
    },
    {
        "slug": "uti",
        "name": "UTI Pattern",
        "note": "Burning urine and frequent urination often suggest a urinary infection.",
        "sym": {"burning_urination": 5, "frequent_urination": 4, "fever": 2, "nausea": 1},
        "foods": ["Water", "Unsweetened fluids", "Light meals"],
        "meds": ["UTIs often need testing and prescription treatment.", "Avoid self-starting leftover antibiotics."],
        "steps": ["Same-day review is best if fever is present.", "Hydration helps but does not replace treatment."],
    },
    {
        "slug": "chest",
        "name": "Chest Infection or Asthma Flare",
        "note": "Cough with breathlessness, wheeze, or chest pain needs careful medical review.",
        "sym": {"cough": 4, "fever": 3, "shortness_of_breath": 4, "wheezing": 4, "chest_pain": 3},
        "foods": ["Warm water", "Broth", "Soft protein-rich meals"],
        "meds": ["Use your prescribed rescue inhaler if you already have one.", "Do not borrow antibiotics or inhalers from someone else."],
        "steps": ["Urgent review is recommended.", "Emergency care is needed if breathing is hard or chest pain is significant."],
    },
    {
        "slug": "dengue",
        "name": "Dengue-like Fever Pattern",
        "note": "High fever with body pain, rash, and joint pain can fit a mosquito-borne fever pattern.",
        "sym": {"fever": 4, "headache": 3, "joint_pain": 4, "rash": 3, "body_ache": 3, "nausea": 2},
        "foods": ["ORS", "Plain fluids", "Coconut water", "Soft foods"],
        "meds": ["Paracetamol may be preferred over aspirin or ibuprofen in some mosquito-borne fever patterns.", "Ask a clinician before using painkillers if dengue is possible."],
        "steps": ["Get medical advice promptly.", "Urgent help is needed for bleeding, severe pain, or extreme weakness."],
    },
    {
        "slug": "diabetes",
        "name": "Diabetes Warning Pattern",
        "note": "Frequent urination with thirst and blurred vision should be checked with a blood sugar test.",
        "sym": {"excessive_thirst": 5, "frequent_urination": 4, "fatigue": 2, "blurred_vision": 3, "dry_mouth": 2},
        "foods": ["Water", "Balanced meals", "High-fiber vegetables"],
        "meds": ["Testing matters more than self-starting medication.", "Do not begin diabetes tablets without a clinician confirming the diagnosis."],
        "steps": ["Arrange a clinician visit and blood sugar check.", "Urgent care is needed if vomiting, confusion, or deep breathing appears."],
    },
    {
        "slug": "anxiety",
        "name": "Anxiety or Stress Pattern",
        "note": "Stress can trigger palpitations, dizziness, poor sleep, and breathing discomfort.",
        "sym": {"palpitations": 4, "dizziness": 2, "insomnia": 3, "shortness_of_breath": 2, "headache": 1},
        "foods": ["Water", "Regular meals", "Lower-caffeine drinks"],
        "meds": ["Breathing exercises and rest may help stress symptoms.", "Do not assume anxiety if chest pain or collapse is present."],
        "steps": ["Reduce caffeine and sleep deprivation where possible.", "Seek urgent evaluation for fainting, severe chest pain, or ongoing breathing trouble."],
    },
]

CONDITIONS += [
    {
        "slug": "pneumonia",
        "name": "Pneumonia Warning Pattern",
        "note": "Fever with cough, breathlessness, chest pain, or low energy can suggest a lower-respiratory infection.",
        "sym": {"fever": 4, "cough": 4, "shortness_of_breath": 5, "chest_pain": 3, "fatigue": 2, "chills": 2},
        "foods": ["Warm fluids", "Protein-rich soft meals", "Soup", "Small frequent meals"],
        "meds": ["Pneumonia may need examination and prescription treatment.", "Do not self-start antibiotics without review."],
        "steps": ["Same-day clinical review is recommended if breathing is affected.", "Emergency care is needed for chest pain, blue lips, confusion, or severe breathlessness."],
    },
    {
        "slug": "hypertension",
        "name": "High Blood Pressure Warning Pattern",
        "note": "High BP readings with headache, chest pain, dizziness, or blurred vision need careful assessment.",
        "sym": {"high_bp_reading": 5, "headache": 3, "dizziness": 2, "chest_pain": 4, "blurred_vision": 3, "shortness_of_breath": 3, "palpitations": 2},
        "foods": ["Low-salt meals", "Vegetables", "Fruit", "Water"],
        "meds": ["Do not double BP tablets without medical advice.", "Carry your BP readings when you meet a clinician."],
        "steps": ["Repeat BP after resting for 5 minutes.", "Urgent care is needed for chest pain, severe headache, weakness, or breathlessness."],
    },
    {
        "slug": "thyroid",
        "name": "Thyroid Imbalance Pattern",
        "note": "Weight change, neck swelling, palpitations, tremor, and heat or cold sensitivity can fit thyroid imbalance.",
        "sym": {"neck_swelling": 4, "palpitations": 3, "tremor": 3, "weight_gain": 2, "unexplained_weight_loss": 2, "fatigue": 3, "heat_intolerance": 3, "cold_intolerance": 3},
        "foods": ["Balanced meals", "Protein-rich foods", "Whole grains", "Water"],
        "meds": ["Thyroid tablets need blood-test confirmation and dose monitoring.", "Avoid unprescribed thyroid supplements."],
        "steps": ["Arrange thyroid blood tests if symptoms persist.", "Seek urgent review for very fast heartbeat, chest pain, or severe weakness."],
    },
    {
        "slug": "kidney",
        "name": "Kidney or Urinary Warning Pattern",
        "note": "Swelling, urine changes, flank pain, fever, or urinary burning can suggest kidney or urinary involvement.",
        "sym": {"swelling_feet": 4, "reduced_urine": 4, "flank_pain": 3, "burning_urination": 3, "frequent_urination": 2, "fever": 3, "nausea": 2},
        "foods": ["Water if not fluid-restricted", "Low-salt meals", "Light cooked meals"],
        "meds": ["Avoid painkiller overuse, especially ibuprofen-like medicines, unless a clinician says they are safe.", "Kidney symptoms may need urine and blood tests."],
        "steps": ["Same-day review is best for fever with urinary or flank pain.", "Urgent care is needed if urine output drops sharply or swelling worsens."],
    },
    {
        "slug": "liver",
        "name": "Liver or Jaundice Warning Pattern",
        "note": "Yellow eyes or skin with dark urine, nausea, appetite loss, or abdominal pain should be medically reviewed.",
        "sym": {"yellow_skin": 5, "dark_urine": 4, "nausea": 2, "vomiting": 2, "abdominal_pain": 3, "appetite_loss": 3, "fatigue": 2},
        "foods": ["Small low-fat meals", "Water", "Fruit", "Rice or toast"],
        "meds": ["Avoid alcohol and avoid extra paracetamol until a clinician checks liver safety.", "Bring a list of medicines and supplements to review."],
        "steps": ["Arrange clinical review and liver tests promptly.", "Urgent care is needed for confusion, severe abdominal pain, or repeated vomiting."],
    },
    {
        "slug": "stroke",
        "name": "Stroke Warning Pattern",
        "note": "One-sided weakness, slurred speech, confusion, or sudden severe dizziness can be stroke warning signs.",
        "sym": {"weakness_one_side": 5, "slurred_speech": 5, "confusion": 4, "dizziness": 2, "headache": 2, "blurred_vision": 2, "high_bp_reading": 2},
        "foods": ["Do not delay care for food or home treatment"],
        "meds": ["Do not self-medicate during possible stroke symptoms.", "Emergency assessment decides safe treatment."],
        "steps": ["Call emergency services immediately for sudden face, arm, speech, or balance symptoms.", "Note the exact time symptoms started."],
    },
    {
        "slug": "parkinsons",
        "name": "Parkinsonian Movement Pattern",
        "note": "Tremor with slow movement, stiffness, or balance change can fit a movement-disorder pattern.",
        "sym": {"tremor": 5, "slow_movement": 4, "fatigue": 1, "dizziness": 1, "insomnia": 2},
        "foods": ["Fiber-rich meals", "Water", "Protein-balanced meals"],
        "meds": ["Movement-disorder medicines require neurologist guidance.", "Do not stop prescribed neurologic medicines suddenly."],
        "steps": ["Book a non-emergency clinician or neurology review if symptoms are gradual.", "Urgent review is needed for sudden weakness, speech trouble, or confusion."],
    },
    {
        "slug": "breast",
        "name": "Breast Change Warning Pattern",
        "note": "A new breast lump, nipple discharge, or unexplained breast change should be assessed in person.",
        "sym": {"breast_lump": 5, "nipple_discharge": 4, "unexplained_weight_loss": 2, "fatigue": 1, "night_sweats": 1},
        "foods": ["Balanced meals", "Protein-rich foods", "Fruit and vegetables"],
        "meds": ["Avoid starting antibiotics or hormone medicines without examination.", "Pain relief choices should consider allergies and current medicines."],
        "steps": ["Schedule clinical breast examination promptly.", "Seek urgent care for fever with a painful red swollen breast."],
    },
    {
        "slug": "lung",
        "name": "Chronic Lung Disease Warning Pattern",
        "note": "Persistent cough with breathlessness, wheeze, weight loss, blood in sputum, or night sweats needs evaluation.",
        "sym": {"cough": 3, "shortness_of_breath": 4, "wheezing": 3, "coughing_blood": 5, "unexplained_weight_loss": 3, "night_sweats": 3, "chest_pain": 2},
        "foods": ["Small protein-rich meals", "Warm fluids", "Water"],
        "meds": ["Use only prescribed inhalers as directed.", "Coughing blood or weight loss should not be treated only with cough syrup."],
        "steps": ["Arrange medical review for cough lasting more than 2-3 weeks.", "Emergency care is needed for coughing blood, severe breathlessness, or chest pain."],
    },
]


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")
    if not REPORTS_FILE.exists():
        REPORTS_FILE.write_text("[]", encoding="utf-8")


def read_store(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_store(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def uniq(items: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def ordered_ids(ids: set[str]) -> list[str]:
    return [item["id"] for item in SYMPTOMS if item["id"] in ids]


def labels(ids: list[str]) -> list[str]:
    return [LOOKUP[item]["label"] for item in ids if item in LOOKUP]


def note_symptoms(notes: str) -> list[str]:
    text = normalize(notes)
    found: list[str] = []
    for symptom in SYMPTOMS:
        if any(normalize(key) in text for key in symptom["keys"]):
            found.append(symptom["id"])
    return uniq(found)


def parse_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def get_user_by_email(email: str):
    users = read_store(USERS_FILE)
    return next((user for user in users if user["email"] == email), None)


def get_user(user_id: int):
    users = read_store(USERS_FILE)
    return next((user for user in users if user["id"] == user_id), None)


def add_user(full_name: str, email: str, password: str) -> int:
    users = read_store(USERS_FILE)
    next_id = max((user["id"] for user in users), default=0) + 1
    users.append(
        {
            "id": next_id,
            "full_name": full_name,
            "email": email,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    write_store(USERS_FILE, users)
    return next_id


def save_report(user_id: int, report: dict) -> int:
    reports = read_store(REPORTS_FILE)
    next_id = max((item["id"] for item in reports), default=0) + 1
    reports.append({"id": next_id, "user_id": user_id, "created_at": report["created_at_iso"], "report": report})
    write_store(REPORTS_FILE, reports)
    return next_id


def load_report(user_id: int, report_id: int):
    reports = read_store(REPORTS_FILE)
    row = next((item for item in reports if item["id"] == report_id and item["user_id"] == user_id), None)
    if not row:
        return None
    data = row["report"]
    data["report_id"] = row["id"]
    return data


def latest_report(user_id: int):
    reports = [item for item in read_store(REPORTS_FILE) if item["user_id"] == user_id]
    if not reports:
        return None
    row = sorted(reports, key=lambda item: item["id"], reverse=True)[0]
    data = row["report"]
    data["report_id"] = row["id"]
    return data


def report_total(user_id: int) -> int:
    return len([item for item in read_store(REPORTS_FILE) if item["user_id"] == user_id])


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to open the dashboard.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def condition_adjustment(condition: dict, context: dict | None) -> int:
    if not context:
        return 0
    slug = condition["slug"]
    age = context.get("age")
    days = context.get("days")
    temp_c = context.get("temp_c")
    pain = context.get("pain")
    known_conditions = normalize(context.get("known_conditions", ""))
    bonus = 0

    if temp_c and temp_c >= 38.0 and slug in {"flu", "covid", "pneumonia", "dengue", "gastroenteritis", "kidney"}:
        bonus += 7
    if temp_c and temp_c >= 38.5 and slug in {"cold", "allergy", "thyroid", "parkinsons"}:
        bonus -= 6
    if days and days >= 7 and slug in {"pneumonia", "lung", "kidney", "liver"}:
        bonus += 5
    if age and age >= 45 and slug in {"diabetes", "hypertension", "stroke", "kidney", "lung"}:
        bonus += 4
    if pain and pain >= 8 and slug in {"migraine", "gastroenteritis", "dengue", "kidney", "liver"}:
        bonus += 3
    if "diabetes" in known_conditions and slug in {"diabetes", "kidney", "hypertension"}:
        bonus += 4
    if any(term in known_conditions for term in ["asthma", "copd", "bronchitis"]) and slug in {"chest", "pneumonia", "lung"}:
        bonus += 4
    if any(term in known_conditions for term in ["bp", "blood pressure", "hypertension"]) and slug in {"hypertension", "stroke"}:
        bonus += 4
    return bonus


def confidence_label(score: int, matched_count: int) -> str:
    if score >= 78 and matched_count >= 3:
        return "High confidence"
    if score >= 58 and matched_count >= 2:
        return "Moderate confidence"
    return "Needs more information"


def score_condition(selected: list[str], condition: dict, context: dict | None = None) -> dict:
    picked = set(selected)
    matched = [symptom for symptom in condition["sym"] if symptom in picked]
    matched_weight = sum(condition["sym"][symptom] for symptom in matched)
    total_weight = sum(condition["sym"].values())
    overlap = len(matched) / max(len(picked), 1)
    coverage = matched_weight / total_weight
    selected_weight = sum(condition["sym"].get(symptom, 1) for symptom in picked)
    specificity = matched_weight / max(selected_weight, 1)
    bonus = min(len(matched), 4) * 4
    penalty = 10 if len(picked) == 1 else 0
    score = clamp(round((coverage * 50) + (overlap * 22) + (specificity * 16) + bonus + condition_adjustment(condition, context) - penalty), 5, 96)
    missing = [
        symptom
        for symptom, _weight in sorted(condition["sym"].items(), key=lambda item: item[1], reverse=True)
        if symptom not in picked
    ][:4]
    return {
        "slug": condition["slug"],
        "name": condition["name"],
        "note": condition["note"],
        "score": score,
        "fit": confidence_label(score, len(matched)),
        "evidence": f"{len(matched)} of {len(condition['sym'])} key signals matched",
        "matched": labels(matched),
        "missing_key_symptoms": labels(missing),
        "foods": condition["foods"],
        "meds": condition["meds"],
        "steps": condition["steps"],
    }


def top_conditions(selected: list[str], context: dict | None = None) -> list[dict]:
    scored = [score_condition(selected, condition, context) for condition in CONDITIONS]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:3]


def evidence_quality(selected: list[str], detected: list[str], form: dict) -> dict:
    symptom_points = min(len(selected), 6) * 8
    field_names = ["age", "duration_days", "temperature_c", "pain_level", "known_conditions", "current_medications", "allergies"]
    field_points = sum(7 for field in field_names if form.get(field, "").strip())
    note_points = 9 if form.get("notes", "").strip() else 0
    detected_points = 5 if detected else 0
    score = clamp(symptom_points + field_points + note_points + detected_points, 10, 100)
    missing: list[str] = []
    if len(selected) < 3:
        missing.append("Add at least 3 symptoms when possible.")
    if not form.get("duration_days", "").strip():
        missing.append("Enter symptom duration.")
    if not form.get("temperature_c", "").strip():
        missing.append("Add a measured temperature if fever is possible.")
    if not form.get("pain_level", "").strip():
        missing.append("Enter pain severity from 0 to 10.")
    if not form.get("notes", "").strip():
        missing.append("Describe the symptom story in notes.")
    level = "Strong intake detail" if score >= 76 else "Useful intake detail" if score >= 48 else "Limited intake detail"
    return {"score": score, "level": level, "improvements": missing[:5]}


def clinical_risk_summary(selected: list[str], triage_result: dict, age: int | None, days: int | None, temp_c: float | None, pain: int | None, pregnant: str) -> dict:
    base = {"routine": 28, "urgent": 66, "critical": 90}.get(triage_result["style"], 35)
    drivers = list(triage_result["alerts"])
    if age and age >= 65:
        base += 6
        drivers.append("Age over 65 raises clinical risk.")
    if days and days >= 5:
        base += 5
        drivers.append("Symptoms have lasted 5 or more days.")
    if temp_c and temp_c >= 39.0:
        base += 6
        drivers.append("Temperature is high.")
    if pain and pain >= 8:
        base += 5
        drivers.append("Pain score is severe.")
    if pregnant in {"yes", "possible"}:
        base += 5
        drivers.append("Pregnancy status changes triage and medicine safety.")
    if set(selected) & RED_FLAGS:
        base += 8
        drivers.append("A red-flag symptom was selected.")
    score = clamp(base, 5, 98)
    band = "High" if score >= 75 else "Medium" if score >= 45 else "Low"
    return {"score": score, "band": band, "drivers": uniq(drivers)[:6]}


def follow_up_questions(results: list[dict], selected: list[str], form: dict, age: int | None, days: int | None, temp_c: float | None, pain: int | None) -> list[str]:
    questions: list[str] = []
    picked = set(selected)
    if age is None:
        questions.append("Confirm the patient's age because age changes risk for infection, stroke, BP, kidney, and heart patterns.")
    if days is None:
        questions.append("How many days have the symptoms been present, and are they improving or worsening?")
    if temp_c is None and any(item["slug"] in {"flu", "covid", "pneumonia", "dengue", "kidney", "gastroenteritis"} for item in results):
        questions.append("Measure temperature with a thermometer to separate fever patterns from non-fever patterns.")
    if pain is None and any(symptom in picked for symptom in ["headache", "abdominal_pain", "chest_pain", "flank_pain"]):
        questions.append("Rate pain from 0 to 10 and note whether it is sudden, severe, or spreading.")
    for item in results[:2]:
        missing = item.get("missing_key_symptoms", [])[:2]
        if missing:
            questions.append(f"For {item['name']}, check whether {', '.join(missing)} is also present.")
    if picked & RED_FLAGS:
        questions.append("For red-flag symptoms, confirm when they started and whether emergency care is already being arranged.")
    return uniq(questions)[:6]


def triage(selected: list[str], age: int | None, days: int | None, temp_c: float | None, pain: int | None, pregnant: str) -> dict:
    picked = set(selected)
    alerts: list[str] = []
    style = "routine"
    title = "Home care and monitoring may be reasonable."

    if picked & RED_FLAGS:
        style = "critical"
        title = "Emergency evaluation is recommended now."
        alerts.append("Red-flag symptoms such as chest pain, one-sided weakness, speech change, confusion, or coughing blood should not be managed only at home.")
    elif {"shortness_of_breath", "chest_pain"} <= picked:
        style = "critical"
        title = "Emergency evaluation is recommended now."
        alerts.append("Chest pain with breathing difficulty should not be managed only at home.")
    elif {"shortness_of_breath", "wheezing"} <= picked or ("fever" in picked and temp_c and temp_c >= 39.0):
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Breathing symptoms or high fever can worsen quickly.")

    if days and days >= 5 and style == "routine":
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Symptoms lasting several days without improvement should be checked.")

    if {"vomiting", "diarrhea"} <= picked and ("dizziness" in picked or "dry_mouth" in picked) and style == "routine":
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Vomiting or diarrhea with dehydration signs needs closer assessment.")

    if {"burning_urination", "fever"} <= picked and style == "routine":
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Fever with urinary symptoms can suggest a deeper infection.")

    if pain and pain >= 8 and style == "routine":
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Severe pain needs in-person assessment.")

    if pregnant in {"yes", "possible"} and ("fever" in picked or "abdominal_pain" in picked or "shortness_of_breath" in picked) and style == "routine":
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Pregnancy changes which symptoms and medicines are safe to manage at home.")

    if age and age >= 65 and ("fever" in picked or "shortness_of_breath" in picked) and style == "routine":
        style = "urgent"
        title = "Urgent same-day clinical review is recommended."
        alerts.append("Older adults can become unwell more quickly with infection or breathing symptoms.")

    if not alerts:
        alerts.append("No red flag was detected from the entered answers, but symptoms should still be monitored.")

    return {"style": style, "title": title, "alerts": alerts}


def gather_foods(results: list[dict]) -> list[str]:
    foods = ["Water or ORS in small steady sips", "Light easy-to-digest meals"]
    for item in results:
        foods.extend(item["foods"])
    return uniq(foods)[:8]


def gather_meds(results: list[dict], pregnant: str, current_meds: str, allergies: str, known_conditions: str) -> list[str]:
    notes: list[str] = []
    if pregnant in {"yes", "possible"} or current_meds or allergies or known_conditions:
        notes.append("Because pregnancy, allergies, current medicines, or chronic conditions were reported, ask a clinician or pharmacist before taking new tablets.")
    for item in results:
        notes.extend(item["meds"])
    notes.append("Avoid leftover antibiotics, steroids, or borrowed prescription medicines.")
    return uniq(notes)[:8]


def gather_steps(results: list[dict], triage_result: dict) -> list[str]:
    steps = [triage_result["title"], *triage_result["alerts"]]
    for item in results:
        steps.extend(item["steps"])
    return uniq(steps)[:8]


def build_report(user: dict, form: dict, selected: list[str], detected: list[str]) -> dict:
    now = datetime.now()
    age = parse_int(form.get("age"))
    days = parse_int(form.get("duration_days"))
    temp_c = parse_float(form.get("temperature_c"))
    pain = parse_int(form.get("pain_level"))
    pregnant = form.get("pregnancy_status", "not_applicable")
    picked = set(selected)
    if temp_c is not None and temp_c >= 37.8:
        picked.add("fever")
    selected = ordered_ids(picked)
    current_meds = form.get("current_medications", "").strip()
    allergies = form.get("allergies", "").strip()
    known_conditions = form.get("known_conditions", "").strip()
    context = {
        "age": age,
        "days": days,
        "temp_c": temp_c,
        "pain": pain,
        "pregnant": pregnant,
        "known_conditions": known_conditions,
    }
    results = top_conditions(selected, context)
    triage_result = triage(selected, age, days, temp_c, pain, pregnant)
    quality = evidence_quality(selected, detected, form)
    risk = clinical_risk_summary(selected, triage_result, age, days, temp_c, pain, pregnant)
    return {
        "created_at_display": now.strftime("%d %b %Y, %I:%M %p"),
        "created_at_iso": now.isoformat(timespec="seconds"),
        "created_at_compact": now.strftime("%Y%m%d_%H%M%S"),
        "patient": {
            "name": form.get("patient_name", "").strip() or user["full_name"],
            "email": user["email"],
            "age": age or "",
            "gender": form.get("gender", ""),
            "pregnancy_status": pregnant,
        },
        "submitted": {
            "symptom_ids": selected,
            "symptoms": labels(selected),
            "note_matches": labels(detected),
            "notes": form.get("notes", "").strip(),
            "duration_days": days or "",
            "temperature_c": f"{temp_c:.1f}" if temp_c is not None else "",
            "pain_level": pain if pain is not None else "",
            "known_conditions": known_conditions,
            "current_medications": current_meds,
            "allergies": allergies,
        },
        "triage": triage_result,
        "risk_summary": risk,
        "evidence_quality": quality,
        "predictions": results,
        "follow_up_questions": follow_up_questions(results, selected, form, age, days, temp_c, pain),
        "foods": gather_foods(results),
        "med_guidance": gather_meds(results, pregnant, current_meds, allergies, known_conditions),
        "next_steps": gather_steps(results, triage_result),
        "disclaimer": "This portal provides AI-assisted screening support only. It is not a confirmed diagnosis and must not replace emergency or in-person medical care.",
    }


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "patient"


@app.get("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html", active_tab=request.args.get("mode", "login"))


@app.post("/register")
def register():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    if not full_name or not email or not password:
        flash("Please complete every register field.", "error")
        return redirect(url_for("home", mode="register"))
    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("home", mode="register"))
    if len(password) < 8:
        flash("Use at least 8 characters for the password.", "error")
        return redirect(url_for("home", mode="register"))
    if get_user_by_email(email):
        flash("That email is already registered. Please log in instead.", "error")
        return redirect(url_for("home", mode="login"))
    session["user_id"] = add_user(full_name, email, password)
    flash("Registration complete. Your portal is ready.", "success")
    return redirect(url_for("dashboard"))


@app.post("/login")
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return redirect(url_for("home", mode="login"))
    session["user_id"] = user["id"]
    flash("Welcome back to MediScope AI.", "success")
    return redirect(url_for("dashboard"))


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.get("/dashboard")
@login_required
def dashboard():
    user = get_user(int(session["user_id"]))
    picked_report = request.args.get("report", type=int)
    report = load_report(user["id"], picked_report) if picked_report else latest_report(user["id"])
    return render_template(
        "dashboard.html",
        user=user,
        symptoms=SYMPTOMS,
        report=report,
        report_count=report_total(user["id"]),
        today_label=datetime.now().strftime("%A, %d %B %Y"),
        report_just_generated=bool(picked_report),
    )


@app.post("/predict")
@login_required
def predict():
    user = get_user(int(session["user_id"]))
    selected = [item for item in request.form.getlist("symptoms") if item in LOOKUP]
    notes = request.form.get("notes", "").strip()
    detected = [item for item in note_symptoms(notes) if item not in selected]
    chosen = ordered_ids(set(selected) | set(detected))
    if not chosen:
        flash("Select at least one symptom or describe symptoms in the notes field.", "error")
        return redirect(url_for("dashboard"))
    report = build_report(user, request.form.to_dict(), chosen, detected)
    report_id = save_report(user["id"], report)
    flash("Medical screening report generated.", "success")
    return redirect(url_for("dashboard", report=report_id))


@app.get("/download-report/<int:report_id>")
@login_required
def download_report(report_id: int):
    user = get_user(int(session["user_id"]))
    report = load_report(user["id"], report_id)
    if not report:
        flash("That report could not be found.", "error")
        return redirect(url_for("dashboard"))
    response = make_response(render_template("report_download.html", report=report))
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{safe_name(report["patient"]["name"])}_medical_report_{report["created_at_compact"]}.html"'
    return response


init_db()


if __name__ == "__main__":
    app.run(debug=True)
