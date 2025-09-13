from transformers import T5Tokenizer, T5ForConditionalGeneration
from torch import torch

# Load the tokenizer and model
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")

# Ensure the model is on the appropriate device (CPU or GPU)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

# Example input text
input_text = "summarize: The quick brown fox jumps over the lazy dog. The dog was sleeping peacefully in the sun."
input_ids = tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True).input_ids.to(device)

# Generate output
outputs = model.generate(input_ids, max_length=50, num_beams=4, early_stopping=True)
summary = tokenizer.decode(outputs[0], skip_special_tokens=True)

print("Summary:", summary)
