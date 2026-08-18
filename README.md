# AI Based Disease Prediction App

MediScope AI is a Flask-based medical screening portal with login, patient intake, symptom prediction, food guidance, medicine caution notes, report saving, and downloadable HTML reports.

## New accuracy and innovation upgrades

- Evidence-aware triage engine with expanded disease patterns for pneumonia, hypertension, thyroid imbalance, kidney/urinary warnings, liver/jaundice warnings, stroke warning signs, Parkinsonian movement patterns, breast changes, lung warning signs, diabetes, dengue, flu, COVID-like illness, allergy, migraine, UTI, and more.
- Smarter scoring that considers matched symptoms, missing key symptoms, symptom specificity, fever, duration, age, pain level, and known conditions.
- Clinical risk meter, input quality meter, matched evidence, missing symptom hints, and smart follow-up questions in both the dashboard and downloaded report.
- Reusable ML training pipeline in `train_models.py` to retrain disease models from real CSV datasets using cross-validation and model comparison.

## Run the app

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Train higher-accuracy models

The current CSV files in `datasets/` are placeholders. Replace them with real datasets that include feature columns and a target column such as `target`, `diagnosis`, `disease`, `class`, `label`, `result`, or `status`.

Train every dataset:

```bash
python train_models.py
```

Train one dataset with an explicit target column:

```bash
python train_models.py --dataset datasets/heart.csv --target target
```

Preview validation without writing model files:

```bash
python train_models.py --dry-run
```

The script compares Logistic Regression, Random Forest, and Extra Trees using stratified cross-validation, then saves the best pipeline as `models/<dataset>_model.pkl` and writes metrics to `models/model_metrics.json`.

## Important note

This project provides educational screening support only. It is not a confirmed diagnosis and must not replace emergency or in-person medical care.
