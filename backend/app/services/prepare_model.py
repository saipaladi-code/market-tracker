"""
Model Preparation Build Script
------------------------------
Executed during the Render build phase (pip install -r requirements.txt && python -m app.services.prepare_model).
Runs on Render's high-memory build cluster (4-8 GB RAM) to download ProsusAI/finbert,
cast weights directly to bfloat16 safetensors, and save to data/finbert_bfloat16/.

At container runtime (which has Render's strict 512 MB RAM limit), the web service loads
directly from this pre-serialized bfloat16 format, avoiding any dynamic type conversion or
intermediate memory spikes, keeping peak resident memory strictly at ~389 MB.
"""

import os
import gc
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_model")

MODEL_NAME = "ProsusAI/finbert"
TARGET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "finbert_bfloat16")

def prepare():
    os.makedirs(TARGET_DIR, exist_ok=True)
    safetensors_path = os.path.join(TARGET_DIR, "model.safetensors")

    if os.path.exists(safetensors_path) and os.path.getsize(safetensors_path) > 100 * 1024 * 1024:
        logger.info(f"Target model already exists in {TARGET_DIR} ({os.path.getsize(safetensors_path)/(1024*1024):.1f} MB). Skipping preparation.")
        return

    logger.info(f"Downloading and converting {MODEL_NAME} to bfloat16 safetensors on build machine...")
    torch.set_grad_enabled(False)

    logger.info("Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    tokenizer.save_pretrained(TARGET_DIR)

    logger.info("Loading model in bfloat16...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16
    )
    model.eval()

    logger.info(f"Serializing bfloat16 model to {TARGET_DIR}...")
    model.save_pretrained(TARGET_DIR, safe_serialization=True)

    del model, tokenizer
    gc.collect()

    logger.info(f"Model successfully prepared at {TARGET_DIR}.")
    for f in os.listdir(TARGET_DIR):
        fpath = os.path.join(TARGET_DIR, f)
        logger.info(f"  - {f}: {os.path.getsize(fpath)/(1024*1024):.2f} MB")

if __name__ == "__main__":
    prepare()
