# prepare_fixed.py
import pandas as pd
import string
import os

# -------------------------------------------------
# 1. Load CSV
# -------------------------------------------------
df = pd.read_csv("parallel_corpus.csv", dtype=str)  # force str to avoid NaN issues
print(f"Loaded {len(df)} rows")
print("Columns:", list(df.columns))

# -------------------------------------------------
# 2. Safe validation
# -------------------------------------------------
def is_valid(t):
    if not isinstance(t, str):
        return False
    s = t.strip()
    return len(s) > 0 and s not in string.punctuation

# -------------------------------------------------
# 3. Build pairs — ONLY if BOTH exist
# -------------------------------------------------
pairs = []

# Breton
br = df[df["koad21_text"].apply(is_valid) & df["niv_text"].apply(is_valid)]
for _, row in br.iterrows():
    pairs.append({
        "text": f"translate English to br: {row['niv_text'].strip()}",
        "target": row["koad21_text"].strip()
    })

# Welsh
cy = df[df["bcnda_text"].apply(is_valid) & df["niv_text"].apply(is_valid)]
for _, row in cy.iterrows():
    pairs.append({
        "text": f"translate English to cy: {row['niv_text'].strip()}",
        "target": row["bcnda_text"].strip()
    })

# Cornish
kw = df[df["abk_text"].apply(is_valid) & df["niv_text"].apply(is_valid)]
for _, row in kw.iterrows():
    pairs.append({
        "text": f"translate English to kw: {row['niv_text'].strip()}",
        "target": row["abk_text"].strip()
    })

final_df = pd.DataFrame(pairs)
print(f"Total valid pairs: {len(final_df)}")

# -------------------------------------------------
# 4. Split
# -------------------------------------------------
final_df = final_df.sample(frac=1, random_state=42).reset_index(drop=True)
split = int(0.8 * len(final_df))
train_df = final_df.iloc[:split]
valid_df = final_df.iloc[split:]

# -------------------------------------------------
# 5. SAVE CORRECTLY — with proper escaping
# -------------------------------------------------
os.makedirs("autotrain-project", exist_ok=True)

train_df.to_csv(
    "autotrain-project/train.csv",
    index=False,
    quoting=1,  # csv.QUOTE_ALL
    escapechar='\\'
)

valid_df.to_csv(
    "autotrain-project/valid.csv",
    index=False,
    quoting=1,
    escapechar='\\'
)

print(f"Saved:")
print(f"  train.csv  → {len(train_df)} rows")
print(f"  valid.csv  → {len(valid_df)} rows")