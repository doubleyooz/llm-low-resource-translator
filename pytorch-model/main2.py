import json
import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments
import evaluate
import torch
import string

print(f'PyTorch: {torch.__version__}, GPU: {torch.cuda.is_available()}, Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"}')

# 1. Load and preprocess the data
try:
    with open("parallel_corpus.json", "r", encoding="utf-8") as file:
        data = json.load(file)
        print(f"Loaded {len(data)} entries from parallel_corpus.json")
except FileNotFoundError:
    print("Error: The file 'parallel_corpus.json' was not found.")
    exit(1)
except json.JSONDecodeError:
    print("Error: Failed to decode JSON from the file. Check for malformed JSON.")
    exit(1)

# Convert to DataFrame
df = pd.DataFrame(data)

# Check if expected columns exist
expected_columns = ["niv_text", "koad21_text", "abk_text", "bcnda_text"]
if not all(col in df.columns for col in expected_columns):
    print(f"Error: JSON data missing expected columns: {expected_columns}")
    exit(1)

# Filter and combine datasets
def is_valid_text(text):
    if not text or text.strip() == "" or text.strip() in string.punctuation:
        return False
    return True

# Create language-specific DataFrames with language identifier
breton_df = df[df.apply(lambda x: is_valid_text(x["niv_text"]) and is_valid_text(x["koad21_text"]), axis=1)][["niv_text", "koad21_text"]].rename(columns={"niv_text": "en", "koad21_text": "target"})
breton_df["language"] = "br"
cornish_df = df[df.apply(lambda x: is_valid_text(x["niv_text"]) and is_valid_text(x["abk_text"]), axis=1)][["niv_text", "abk_text"]].rename(columns={"niv_text": "en", "abk_text": "target"})
cornish_df["language"] = "abk"
welsh_df = df[df.apply(lambda x: is_valid_text(x["niv_text"]) and is_valid_text(x["bcnda_text"]), axis=1)][["niv_text", "bcnda_text"]].rename(columns={"niv_text": "en", "bcnda_text": "target"})
welsh_df["language"] = "cy"

# Combine into a single DataFrame
combined_df = pd.concat([breton_df, cornish_df, welsh_df], ignore_index=True)
print(f"Combined dataset size: {len(combined_df)} pairs (Breton: {len(breton_df)}, Cornish: {len(cornish_df)}, Welsh: {len(welsh_df)})")

# Convert to Hugging Face Dataset
dataset = Dataset.from_pandas(combined_df)

# Split into train and test (80% train, 20% test)
dataset = dataset.train_test_split(test_size=0.2, seed=42)
raw_datasets = DatasetDict({
    "train": dataset["train"],
    "test": dataset["test"]
})

# 2. Load tokenizer and model
try:
    print("Loading previous tokenizer...")
    tokenizer = T5Tokenizer.from_pretrained("./t5_multilingual")
    print("Loading previous T5 model...")
    model = T5ForConditionalGeneration.from_pretrained("./t5_multilingual")
except Exception as e:
    print("Loading tokenizer...")
    tokenizer = T5Tokenizer.from_pretrained("t5-small")
    print("Tokenizer loaded successfully.")
    model = T5ForConditionalGeneration.from_pretrained("t5-small")



print("Model loaded successfully.")
device = "cpu"  # Force CPU to avoid freeze
print(f"Moving model to device: {device}")
model = model.to(device)
print("Model moved to device successfully.")

# 3. Tokenize the datasets
def preprocess_function(examples):
    inputs = [f"translate English to {lang}: {en}" for lang, en in zip(examples["language"], examples["en"])]
    targets = examples["target"]
    model_inputs = tokenizer(inputs, max_length=128, truncation=True, padding="max_length")
    labels = tokenizer(targets, max_length=128, truncation=True, padding="max_length").input_ids
    model_inputs["labels"] = labels
    return model_inputs

print("Tokenizing datasets...")
raw_datasets["train"] = raw_datasets["train"].map(preprocess_function, batched=True)
raw_datasets["test"] = raw_datasets["test"].map(preprocess_function, batched=True)

# 4. Set up training arguments
print("Setting up training arguments...")
training_args = TrainingArguments(
    output_dir="./t5_multilingual",
    eval_steps=500,
    learning_rate=4e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    eval_strategy="steps",
    save_strategy="steps",
    save_steps=500,
    save_total_limit=2,
    logging_dir='./logs',
    logging_steps=20,
    greater_is_better=False,
    load_best_model_at_end=True,
    fp16=False
)

# 5. Define compute_metrics function
metric = evaluate.load("sacrebleu")
print("Loaded sacrebleu metric.")
def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    labels = [[label] for label in tokenizer.batch_decode(labels, skip_special_tokens=True)]
    return metric.compute(predictions=decoded_preds, references=labels)

# 6. Train the model
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=raw_datasets["train"],
    eval_dataset=raw_datasets["test"],
    compute_metrics=compute_metrics,
)
trainer.train()
trainer.save_model("./t5_multilingual")

# 7. Example inference
def translate(text, model_path, target_lang):
    model = T5ForConditionalGeneration.from_pretrained(model_path).to(device)
    input_text = f"translate English to {target_lang}: {text}"
    input_ids = tokenizer(input_text, return_tensors="pt", max_length=128, truncation=True).input_ids.to(device)
    outputs = model.generate(input_ids, max_length=128, num_beams=4, early_stopping=True)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Test translations
test_text = "You trampled the sea with your horses, churning the great waters."
breton_translation = translate(test_text, "./t5_multilingual", "Breton")
cornish_translation = translate(test_text, "./t5_multilingual", "Cornish")
welsh_translation = translate(test_text, "./t5_multilingual", "Welsh")
print("Breton Translation:", breton_translation)
print("Cornish Translation:", cornish_translation)
print("Welsh Translation:", welsh_translation)