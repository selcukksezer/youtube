"""
Video Binary Variation, MP4 Atom Padding & Hash Disruption
Covers items: 30
"""
import os, random, struct, hashlib
from typing import Dict, Any

def apply_video_size_variation(video_path: str) -> Dict[str, Any]:
    """
    Applies compliant micro-size variation to MP4 video using a standard 'free' atom (Rule 30).
    Guarantees every uploaded video has a unique byte size and unique SHA-256/MD5 hash,
    completely defeating YouTube duplicate template filters without re-encoding!
    """
    if not os.path.exists(video_path):
        return {
            "success": False,
            "error": f"Dosya bulunamadı: {video_path}"
        }

    orig_size = os.path.getsize(video_path)
    
    # Calculate original MD5
    hasher = hashlib.md5()
    with open(video_path, "rb") as f:
        chunk = f.read(65536)
        while chunk:
            hasher.update(chunk)
            chunk = f.read(65536)
    orig_md5 = hasher.hexdigest()

    # Variable padding between 450KB and 1.25MB (Rule 30: 1-2 MB variation)
    padding_bytes = random.randint(480000, 1280000)
    atom_size = padding_bytes + 8
    header = struct.pack(">I", atom_size) + b"free"
    entropy_payload = os.urandom(padding_bytes)

    with open(video_path, "ab") as f:
        f.write(header + entropy_payload)

    new_size = os.path.getsize(video_path)
    delta_kb = round((new_size - orig_size) / 1024, 1)

    # Calculate new MD5
    new_hasher = hashlib.md5()
    with open(video_path, "rb") as f:
        chunk = f.read(65536)
        while chunk:
            new_hasher.update(chunk)
            chunk = f.read(65536)
    new_md5 = new_hasher.hexdigest()

    return {
        "success": True,
        "video_path": video_path,
        "original_size_bytes": orig_size,
        "new_size_bytes": new_size,
        "original_size_mb": round(orig_size / (1024 * 1024), 2),
        "new_size_mb": round(new_size / (1024 * 1024), 2),
        "delta_kb": delta_kb,
        "original_md5": orig_md5,
        "new_unique_md5": new_md5,
        "padding_atom": "free (ISO/IEC 14496-12 standardı)",
        "info": f"Kural 30 Boyut Varyasyonu: +{delta_kb} KB özgün dolgu eklendi ({orig_md5[:8]}... -> {new_md5[:8]}...). Şablon benzerliği engellendi."
    }
