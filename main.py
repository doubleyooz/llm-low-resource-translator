import json
import pandas as pd
from datasets import Dataset, DatasetDict
from transformers import T5Tokenizer, T5ForConditionalGeneration, Trainer, TrainingArguments
import evaluate
import torch
import string

# 1. Load and preprocess the data
# Load JSON file
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

# Filter out invalid entries
def is_valid_text(text):
    if not text or text.strip() == "" or text.strip() in string.punctuation:
        return False
    return True

# Filter rows where both source and target texts are valid
breton_df = df[df.apply(lambda x: is_valid_text(x["niv_text"]) and is_valid_text(x["koad21_text"]), axis=1)][["niv_text", "koad21_text"]].rename(columns={"niv_text": "en", "koad21_text": "br"})
cornish_df = df[df.apply(lambda x: is_valid_text(x["niv_text"]) and is_valid_text(x["abk_text"]), axis=1)][["niv_text", "abk_text"]].rename(columns={"niv_text": "en", "abk_text": "abk"})
welsh_df = df[df.apply(lambda x: is_valid_text(x["niv_text"]) and is_valid_text(x["bcnda_text"]), axis=1)][["niv_text", "bcnda_text"]].rename(columns={"niv_text": "en", "bcnda_text": "cy"})

# Print number of valid pairs
print(f"Valid Breton pairs: {len(breton_df)}")
print(f"Valid Cornish pairs: {len(cornish_df)}")
print(f"Valid Welsh pairs: {len(welsh_df)}")

# Convert to Hugging Face Datasets
breton_dataset = Dataset.from_pandas(breton_df)
cornish_dataset = Dataset.from_pandas(cornish_df)
welsh_dataset = Dataset.from_pandas(welsh_df)

# Split into train and test (80% train, 20% test)
breton_dataset = breton_dataset.train_test_split(test_size=0.2, seed=42)
cornish_dataset = cornish_dataset.train_test_split(test_size=0.2, seed=42)
welsh_dataset = welsh_dataset.train_test_split(test_size=0.2, seed=42)

# Combine into DatasetDict
raw_datasets = DatasetDict({
    "breton_train": breton_dataset["train"],
    "breton_test": breton_dataset["test"],
    "cornish_train": cornish_dataset["train"],
    "cornish_test": cornish_dataset["test"],
    "welsh_train": welsh_dataset["train"],
    "welsh_test": welsh_dataset["test"]
})

# 2. Load tokenizer and model
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

# 3. Tokenize the datasets
def preprocess_function(examples, src_lang, tgt_lang, prefix="translate English to "):
    inputs = [prefix + tgt_lang + ": " + en for en in examples[src_lang]]
    targets = examples[tgt_lang]
    model_inputs = tokenizer(inputs, max_length=128, truncation=True, padding="max_length")
    labels = tokenizer(targets, max_length=128, truncation=True, padding="max_length").input_ids
    model_inputs["labels"] = labels
    return model_inputs

# Tokenize datasets
raw_datasets["breton_train"] = raw_datasets["breton_train"].map(
    lambda x: preprocess_function(x, "en", "br", prefix="translate English to Breton: "), batched=True
)
raw_datasets["breton_test"] = raw_datasets["breton_test"].map(
    lambda x: preprocess_function(x, "en", "br", prefix="translate English to Breton: "), batched=True
)
raw_datasets["cornish_train"] = raw_datasets["cornish_train"].map(
    lambda x: preprocess_function(x, "en", "abk", prefix="translate English to Cornish: "), batched=True
)
raw_datasets["cornish_test"] = raw_datasets["cornish_test"].map(
    lambda x: preprocess_function(x, "en", "abk", prefix="translate English to Cornish: "), batched=True
)
raw_datasets["welsh_train"] = raw_datasets["welsh_train"].map(
    lambda x: preprocess_function(x, "en", "cy", prefix="translate English to Welsh: "), batched=True
)
raw_datasets["welsh_test"] = raw_datasets["welsh_test"].map(
    lambda x: preprocess_function(x, "en", "cy", prefix="translate English to Welsh: "), batched=True
)

print(torch.cuda.is_available())
print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU detected")

# 4. Set up training arguments
training_args = TrainingArguments(
    output_dir="./t5_translation",   
    eval_steps=500,  # Evaluate every 500 steps
    learning_rate=5e-5,
    per_device_train_batch_size=16,  # Adjust based on your GPU memory
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    eval_strategy="steps",
    save_strategy="steps",  # Save more often
    save_steps=500,  # ~6-7 hours at 0.02 it/s
    save_total_limit=2,  # Limit storage use
    logging_dir='./logs',
    logging_steps=10,
    greater_is_better=False,
    load_best_model_at_end=True,
    fp16=True if torch.cuda.is_available() else False
)

# 5. Define compute_metrics function for evaluation
metric = evaluate.load("sacrebleu")

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    labels = [[label] for label in tokenizer.batch_decode(labels, skip_special_tokens=True)]
    return metric.compute(predictions=decoded_preds, references=labels)

# 6. Train the model for Breton
breton_trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=raw_datasets["breton_train"],
    eval_dataset=raw_datasets["breton_test"],
    compute_metrics=compute_metrics,
)
breton_trainer.train()
breton_trainer.save_model("./t5_breton")

# 7. Train the model for Cornish (reinitialize model)
model = T5ForConditionalGeneration.from_pretrained("t5-small").to(device)
cornish_trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=raw_datasets["cornish_train"],
    eval_dataset=raw_datasets["cornish_test"],
    compute_metrics=compute_metrics,
)
cornish_trainer.train()
cornish_trainer.save_model("./t5_cornish")

# 8. Train the model for Welsh (reinitialize model)
model = T5ForConditionalGeneration.from_pretrained("t5-small").to(device)
welsh_trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=raw_datasets["welsh_train"],
    eval_dataset=raw_datasets["welsh_test"],
    compute_metrics=compute_metrics,
)
welsh_trainer.train()
welsh_trainer.save_model("./t5_welsh")

# 9. Example inference
def translate(text, model_path, target_lang):
    model = T5ForConditionalGeneration.from_pretrained(model_path).to(device)
    input_text = f"translate English to {target_lang}: {text}"
    input_ids = tokenizer(input_text, return_tensors="pt", max_length=128, truncation=True).input_ids.to(device)
    outputs = model.generate(input_ids, max_length=128, num_beams=4, early_stopping=True)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Test translations
test_text = "You trampled the sea with your horses, churning the great waters."
breton_translation = translate(test_text, "./t5_breton", "Breton")
cornish_translation = translate(test_text, "./t5_cornish", "Cornish")
welsh_translation = translate(test_text, "./t5_welsh", "Welsh")
print("Breton Translation:", breton_translation)
print("Cornish Translation:", cornish_translation)
print("Welsh Translation:", welsh_translation)