# Optional local MiniMax-H3. Does not start with the app.
# Studio visual engine must be "MiniMax-H3 yerel" before render.
# Listens on http://127.0.0.1:30010 and writes video with stereo audio.
$ErrorActionPreference = "Stop"
$port = 30010
if ($env:MINIMAX_H3_LOCAL_URL -match ":(\d+)\s*$") {
    $port = [int]$Matches[1]
}
$model = if ($env:MINIMAX_H3_MODEL) { $env:MINIMAX_H3_MODEL } else { "MiniMaxAI/MiniMax-H3" }
$gpus = 1
try {
    $rows = @(nvidia-smi --query-gpu=name --format=csv,noheader 2>$null)
    if ($rows.Count -gt 0) { $gpus = $rows.Count }
} catch {
    Write-Host "nvidia-smi yok. MiniMax-H3 yerel sunucu bir NVIDIA GPU ister."
    exit 1
}
if (-not (Get-Command sglang -ErrorAction SilentlyContinue)) {
    Write-Host "sglang komutu yok. Kurulum: pip install 'sglang[diffusion]'"
    Write-Host "Model: $model  (Hugging Face, ilk çalıştırmada iner)"
    exit 1
}
Write-Host "MiniMax-H3 yerel: $model  GPU=$gpus  http://127.0.0.1:$port"
sglang serve `
    --model-path $model `
    --model-variant fl2va `
    --num-gpus $gpus `
    --ulysses-degree $gpus `
    --performance-mode speed `
    --host 127.0.0.1 `
    --port $port
