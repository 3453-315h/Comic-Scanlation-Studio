"""Cryptographic trust and integrity management for AI model artifacts.

Provides scoped, revocable trust records for model weights, linking approved
files to their source URLs and cryptographic digests. Ensures that unverified
models require explicit user confirmation, and that approved artifacts (and their
derived ONNX exports) are checked at every load and across application restarts.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .config import Config

logger = logging.getLogger(__name__)


def get_model_trust_file() -> Path:
    """Return the path to the persistent model trust records JSON file."""
    trust_dir = getattr(Config, 'MODELS_DIR', Config.PORTABLE_DIR / "models")
    return trust_dir / "model_trust.json"


def compute_file_sha256(file_path: Path | str) -> str:
    """Compute the SHA-256 hexadecimal digest of a file in 64KB chunks."""
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found for hash calculation: {file_path}")
    
    hasher = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def load_trust_records() -> Dict[str, Dict[str, Any]]:
    """Load model trust records from disk. Returns empty dict if file does not exist or is invalid."""
    trust_file = get_model_trust_file()
    if not trust_file.exists():
        return {}
    try:
        with open(trust_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        logger.warning(f"Could not read model trust records from {trust_file}: {e}")
    return {}


def save_trust_records(records: Dict[str, Dict[str, Any]]) -> None:
    """Save model trust records to disk atomically."""
    trust_file = get_model_trust_file()
    trust_dir = trust_file.parent
    trust_dir.mkdir(parents=True, exist_ok=True)
    
    import tempfile
    with tempfile.NamedTemporaryFile("w", dir=trust_dir, delete=False, encoding="utf-8") as tf:
        json.dump(records, tf, indent=2)
        tf.flush()
        os.fsync(tf.fileno())
        temp_name = tf.name
    
    os.replace(temp_name, trust_file)


def record_approved_model(
    model_name: str,
    file_path: Path | str,
    source_url: str,
    parent_sha256: Optional[str] = None
) -> str:
    """Record user approval for a specific model artifact.
    
    Computes and stores the exact SHA-256 digest, source URL, timestamp, and optional
    parent model digest (for locally exported ONNX models).
    Returns the computed SHA-256 digest.
    """
    path = Path(file_path)
    sha256_digest = compute_file_sha256(path)
    records = load_trust_records()
    
    record = {
        "model_name": model_name,
        "sha256": sha256_digest,
        "source_url": source_url,
        "file_size": path.stat().st_size,
        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if parent_sha256:
        record["parent_sha256"] = parent_sha256.lower()
        
    records[model_name] = record
    save_trust_records(records)
    logger.info(f"Recorded cryptographic trust for model '{model_name}' (SHA-256: {sha256_digest[:12]}...)")
    return sha256_digest


def revoke_approved_model(model_name: str) -> bool:
    """Revoke trust for a model artifact and any derived models referencing it.
    
    Returns True if a record was removed, False otherwise.
    """
    records = load_trust_records()
    if model_name not in records:
        return False
        
    revoked_record = records.pop(model_name)
    revoked_sha = revoked_record.get("sha256", "").lower()
    
    # Also revoke any child models that were derived from this parent hash
    if revoked_sha:
        children_to_remove = [
            name for name, r in records.items()
            if r.get("parent_sha256", "").lower() == revoked_sha
        ]
        for child in children_to_remove:
            records.pop(child)
            logger.info(f"Cascade revoked trust for derived model '{child}'")
            
    save_trust_records(records)
    logger.info(f"Revoked cryptographic trust for model '{model_name}'")
    return True


def is_model_trusted(file_path: Path | str, model_name: str) -> bool:
    """Check if a model file on disk is trusted.
    
    A file is trusted if:
    1. It matches an official independently-verified pinned SHA-256 in the model registry.
    2. OR its exact SHA-256 matches a stored user approval record for that model name.
       If the record is an exported ONNX model with a parent_sha256, the parent must also be trusted.
    """
    path = Path(file_path)
    if not path.is_file():
        return False
        
    try:
        actual_sha = compute_file_sha256(path)
    except Exception as e:
        logger.error(f"Failed to compute SHA-256 for {path}: {e}")
        return False
        
    # 1. Check official pinned registry if registered
    from ..modules.detector import DETECTOR_MODEL_REGISTRY
    if model_name in DETECTOR_MODEL_REGISTRY:
        pinned_sha = DETECTOR_MODEL_REGISTRY[model_name].get("sha256")
        if pinned_sha and pinned_sha.lower() == actual_sha:
            return True
            
    # 2. Check persistent user trust records
    records = load_trust_records()
    record = records.get(model_name)
    if not record:
        return False
        
    if record.get("sha256", "").lower() != actual_sha:
        logger.warning(
            f"Model file '{model_name}' at {path} does not match trusted hash! "
            f"Expected {record.get('sha256')}, got {actual_sha}."
        )
        return False
        
    # Check parent trust link if present (e.g. ONNX derived from approved PyTorch model)
    parent_sha = record.get("parent_sha256")
    if parent_sha:
        parent_name = model_name.replace(".onnx", ".pt")
        parent_rec = records.get(parent_name)
        if not parent_rec or parent_rec.get("sha256", "").lower() != parent_sha.lower():
            logger.warning(
                f"Derived model '{model_name}' rejected: parent model '{parent_name}' trust is missing or invalid."
            )
            return False

        # If parent model file exists on disk, verify its bytes have not been tampered
        candidate_parent_paths = [
            path.parent / parent_name,
            path.with_name(parent_name),
            path.parent / "yolo" / parent_name,
            path.parent.parent / "yolo" / parent_name,
        ]
        for cp in candidate_parent_paths:
            if cp.is_file():
                if compute_file_sha256(cp) != parent_sha.lower():
                    logger.warning(
                        f"Derived model '{model_name}' rejected: parent model file '{cp}' has been modified or corrupted."
                    )
                    return False
            
    return True


def is_registered_detector(model_name: str | Path) -> bool:
    """Check if model name or its base .pt corresponds to a registered detector model."""
    name = Path(model_name).name
    from ..modules.detector import DETECTOR_MODEL_REGISTRY
    if name in DETECTOR_MODEL_REGISTRY:
        return True
    base_pt = Path(name).with_suffix(".pt").name
    if base_pt in DETECTOR_MODEL_REGISTRY:
        return True
    return False


def get_model_trust_record(model_name: str) -> Optional[Dict[str, Any]]:
    """Get the trust record for a given model name, if it exists."""
    records = load_trust_records()
    return records.get(model_name)
