import os
import subprocess
import sys

REPOS = [
    ("anil_matcha_shorts_generator", "https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator.git"),
    ("shortgpt", "https://github.com/rayventura/shortgpt.git"),
    ("saard00_shorts_generator", "https://github.com/SaarD00/AI-Youtube-Shorts-Generator.git"),
    ("helios", "https://github.com/PKU-YuanGroup/Helios.git"),
    ("short-video-maker", "https://github.com/gyoridavid/short-video-maker.git"),
    ("openshorts", "https://github.com/mutonby/openshorts.git"),
    ("ai-content-studio", "https://github.com/naqashafzal/AI-Content-Studio.git"),
    ("agnes-video-generator", "https://github.com/lcy362/agnes-video-generator.git"),
    ("invideo-ai-nexus", "https://github.com/SurgeBowRetreat/invideo-ai-nexus.git"),
    ("youtube-shorts-pipeline", "https://github.com/rushindrasinha/youtube-shorts-pipeline.git"),
]

def main():
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference_repos")
    os.makedirs(base_dir, exist_ok=True)
    
    results = {}
    for name, url in REPOS:
        target = os.path.join(base_dir, name)
        if os.path.exists(target):
            print(f"[EXISTS] {name}")
            results[name] = "EXISTS"
            continue
            
        print(f"[CLONING] {name} from {url}...")
        sys.stdout.flush()
        cmd = ["git", "clone", "--depth", "1", url, target]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"[SUCCESS] {name}")
            results[name] = "SUCCESS"
        else:
            print(f"[FAILED] {name}: {proc.stderr.strip()}")
            results[name] = f"FAILED: {proc.stderr.strip()}"
        sys.stdout.flush()

    print("\n--- Summary ---")
    for name, status in results.items():
        print(f"{name}: {status}")

if __name__ == "__main__":
    main()
