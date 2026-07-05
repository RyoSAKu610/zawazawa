# Windows 用クイックスタート: エッジスキャンを常時実行して JSONL に蓄積する
# 使い方: PowerShell でこのフォルダ (bot/) に移動して .\run-scan.ps1
# 前提: Python 3.10+ がインストール済み (winget install Python.Python.3.12)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install -q -r requirements.txt

# 60秒間隔で全エッジを実データ計測。ログは logs/edges-YYYYMMDD.jsonl に追記される。
# 止めるときは Ctrl+C。数日回したら `python -m edgebot report` で淘汰レポートを出す。
python -m edgebot scan --loop 60
