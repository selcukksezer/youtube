$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:CAVEMAN_HOME = Join-Path $repo '.caveman-home'
$env:PATH = (Join-Path $repo '.caveman-tools\node_modules\.bin') + ';' + $env:PATH

# Caveman compresses model-visible tool input and keeps recovery data local.
& (Join-Path $repo '.caveman-tools\node_modules\.bin\caveman.cmd') wrap codex @args
