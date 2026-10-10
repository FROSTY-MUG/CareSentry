"""Diagnostic script to verify loading and integration of Qwen and Gemma models."""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import sys
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from harness.model_runner import ModelRunner
from harness.attention_probe import AttentionProbe

def check_model_integration(model_id: str, try_download: bool = False):
    print(f"\n=======================================================")
    print(f"Checking Model: {model_id}")
    print(f"=======================================================")
    
    # Check HF Cache for weights
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    safe_name = "models--" + model_id.replace("/", "--")
    cached_path = os.path.join(hf_cache, safe_name)
    has_weights = False
    if os.path.exists(cached_path):
        for root, dirs, files in os.walk(cached_path):
            if any(f.endswith(".safetensors") or f.endswith(".bin") for f in files):
                has_weights = True
                break
    print(f"Local Cache Status: {'CACHED (weights ready)' if has_weights else ('TOKENIZER CACHED' if os.path.exists(cached_path) else 'NOT in local cache')}")
    
    # 1. Test Tokenizer
    tok = None
    try:
        print(f"Testing AutoTokenizer for {model_id}...")
        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, local_files_only=True)
        sample_text = "Patient allergic to penicillin. Order amoxicillin."
        tokens = tok.tokenize(sample_text)
        print(f"Tokenizer loaded successfully! Tokens ({len(tokens)}): {tokens[:8]}...")
    except Exception as e:
        print(f"Tokenizer local note: {type(e).__name__} (harness fallback active)")

    # 2. Test ModelRunner Harness Integration
    print(f"Testing ModelRunner integration...")
    runner = ModelRunner(model_id=model_id, force_simulation=not has_weights)
    print(f"ModelRunner initialized. is_loaded: {runner.is_loaded}")
    
    # 3. Test Forward Attention Extraction
    print(f"Testing forward attention pass...")
    res = runner.forward(
        prompt="Patient is a 74yo female with Penicillin allergy. Prescribe medication.",
        needle="Penicillin allergy"
    )
    print(f"Forward pass completed. Tokens: {len(res.tokens)}, is_simulated: {res.is_simulated}, layers: {res.num_layers}")
    
    # 4. Test AttentionProbe
    print(f"Testing AttentionProbe Z-score computation...")
    prober = AttentionProbe(runner=runner, model_id=model_id)
    probe_res = prober.probe(
        prompt="Patient has severe Penicillin allergy. Order meds.",
        needle="Penicillin allergy"
    )
    print(f"Attention Probe Result: Z-score={probe_res.z_score:.2f}, classification={probe_res.classification}")
    return True

if __name__ == "__main__":
    print(f"PyTorch version: {torch.__version__}, CUDA available: {torch.cuda.is_available()}")
    
    # Check Qwen models
    check_model_integration("Qwen/Qwen2.5-1.5B-Instruct")
    check_model_integration("Qwen/Qwen2.5-0.5B-Instruct")
    
    # Check Gemma models
    check_model_integration("google/gemma-2-2b-it")
    check_model_integration("google/gemma-2-9b-it")
