import pandas as pd
import torch
from sentence_transformers import SentenceTransformer, util
from sklearn.metrics import classification_report
from tqdm.auto import tqdm
from transformers import pipeline

LABELED_XLSX = "data/labeled.xlsx"
OUTPUT_XLSX = "compare_zero_shot_external_report.xlsx"
SBERT_MODEL = "all-MiniLM-L6-v2"
MNLI_MODEL = "facebook/bart-large-mnli"
CANDIDATES = ["friend", "family", "dating", "professional", "other"]
BATCH_SIZE = 32

# LOAD TEST SET
df = pd.read_excel(LABELED_XLSX)
if "text" not in df.columns or "label" not in df.columns:
    raise KeyError("labeled.xlsx must contain 'text' and 'label' columns")

texts = df["text"].astype(str).tolist()
y_true = df["label"].astype(str).tolist()

# Zero-Shot with BART-MNLI
print("Running zero-shot classification with BART-MNLI…")
zs = pipeline(
    "zero-shot-classification",
    model=MNLI_MODEL,
    device=0 if torch.cuda.is_available() else -1
)
y_pred_mnli = []
for start in tqdm(range(0, len(texts), BATCH_SIZE), desc="MNLI batches"):
    batch = texts[start:start + BATCH_SIZE]
    out = zs(batch, candidate_labels=CANDIDATES, truncation=True, batch_size=BATCH_SIZE)
    y_pred_mnli.extend([r["labels"][0] for r in out])

# Zero-Shot with SBERT-Seed
print("Running zero-shot classification with SBERT-Seed…")
sbert = SentenceTransformer(SBERT_MODEL)
embs = sbert.encode(texts, batch_size=64, show_progress_bar=True)
# Prepare seed sentence embeddings
seed_dict = {
    "friend": [
        "Had a great time hanging out with friends.",
        "Nice place to catch up with buddies.",
        "Perfect for a fun evening with friends.",
        "My college pals and I loved the lively vibe here.",
        "Grabbed drinks with friends after work and it was awesome.",
        "Best spot to celebrate a friend's birthday together.",
        "Met up with my old roommates for a fun reunion dinner.",
        "Great place for a weekend brunch with the gang.",
        "Shared appetizers and laughs with my buddies all night.",
        "Our friend group made this our new go‑to hangout."
    ],

    "family": [
        "Went out with my parents and kids.",
        "Great family‑friendly place.",
        "Perfect for a dinner with mom, dad, and kids.",
        "Brought the whole family for Sunday lunch and everyone was happy.",
        "High chairs and kids' menu made dining with toddlers easy.",
        "Grandma enjoyed the quiet corner table we got.",
        "Spacious enough for our extended family gathering.",
        "Celebrated my sister's graduation with the family here.",
        "The staff was patient with our noisy little ones.",
        "Family reunion dinner felt warm and welcoming."
    ],

    "dating": [
        "Took my girlfriend on a date.",
        "Ideal for a romantic dinner or anniversary.",
        "Perfect spot for couples or lovers.",
        "Candle‑lit tables set the mood for our first date.",
        "My partner loved the cozy two‑top by the window.",
        "Great wine list for a special date night.",
        "Surprised my spouse with an anniversary dessert here.",
        "Lovely ambience for popping the big question.",
        "Quiet corner booths perfect for intimate conversation.",
        "The live jazz made our date unforgettable."
    ],

    "professional": [
        "Had a business lunch with colleagues.",
        "Great for team outings and meetings.",
        "Coworkers and I came here during work.",
        "Met a client here to discuss the new contract.",
        "Convenient location for after‑work networking drinks.",
        "Wi‑Fi and power outlets made it easy to work over coffee.",
        "Reserved a private room for our quarterly team dinner.",
        "Impressed our partners with the professional atmosphere.",
        "Quick service ideal for a tight lunch break with coworkers.",
        "Hosted a small recruiting event in their lounge area."
    ],

    "other": [
        "Food was good but nothing special.",
        "Service was average.",
        "Nice atmosphere and menu.",
        "Stopped by for a quick bite before the movie.",
        "Decent place to grab a late‑night snack.",
        "Menu had plenty of options for everyone.",
        "Overall experience was fine but not exceptional.",
        "Visited while sightseeing and it did the job.",
        "Solid choice when you don't know what you want to eat.",
        "Good spot for a casual solo meal."
    ]
}
seed_vecs = {lab: sbert.encode(sentences, normalize_embeddings=True)
             for lab, sentences in seed_dict.items()}


def classify_seed(vec):
    best_lab, best_sim = "other", -1.0
    for lab, seeds in seed_vecs.items():
        sim = util.cos_sim(vec, seeds).max().item()
        if sim > best_sim:
            best_sim, best_lab = sim, lab
    return best_lab


y_pred_seed = [classify_seed(v) for v in tqdm(embs, desc="SBERT-Seed classify")]

# EVALUATION
print("\n=== BART-MNLI Classification Report ===")
print(classification_report(y_true, y_pred_mnli, labels=CANDIDATES))

print("\n=== SBERT-Seed Classification Report ===")
print(classification_report(y_true, y_pred_seed, labels=CANDIDATES))
