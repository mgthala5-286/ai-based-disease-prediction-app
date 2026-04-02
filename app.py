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
]

LOOKUP = {item["id"]: item for item in SYMPTOMS}
RED_FLAGS = {"chest_pain"}
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


def score_condition(selected: list[str], condition: dict) -> dict:
    picked = set(selected)
    matched = [symptom for symptom in condition["sym"] if symptom in picked]
    matched_weight = sum(condition["sym"][symptom] for symptom in matched)
    total_weight = sum(condition["sym"].values())
    overlap = len(matched) / max(len(picked), 1)
    coverage = matched_weight / total_weight
    bonus = min(len(matched), 4) * 4
    penalty = 10 if len(picked) == 1 else 0
    score = max(5, round((coverage * 55) + (overlap * 28) + bonus - penalty))
    return {
        "slug": condition["slug"],
        "name": condition["name"],
        "note": condition["note"],
        "score": score,
        "fit": "High pattern fit" if score >= 74 and len(matched) >= 3 else "Moderate pattern fit" if score >= 54 and len(matched) >= 2 else "Broad symptom overlap",
        "matched": labels(matched),
        "foods": condition["foods"],
        "meds": condition["meds"],
        "steps": condition["steps"],
    }


def top_conditions(selected: list[str]) -> list[dict]:
    scored = [score_condition(selected, condition) for condition in CONDITIONS]
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:3]


def triage(selected: list[str], age: int | None, days: int | None, temp_c: float | None, pain: int | None, pregnant: str) -> dict:
    picked = set(selected)
    alerts: list[str] = []
    style = "routine"
    title = "Home care and monitoring may be reasonable."

    if picked & RED_FLAGS or {"shortness_of_breath", "chest_pain"} <= picked:
        style = "critical"
        title = "Emergency evaluation is recommended now."
        alerts.append("Chest pain or breathing difficulty should not be managed only at home.")
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
    results = top_conditions(selected)
    triage_result = triage(selected, age, days, temp_c, pain, pregnant)
    current_meds = form.get("current_medications", "").strip()
    allergies = form.get("allergies", "").strip()
    known_conditions = form.get("known_conditions", "").strip()
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
        "predictions": results,
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
