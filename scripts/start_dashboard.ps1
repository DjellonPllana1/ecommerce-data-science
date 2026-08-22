$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m streamlit run dashboard/app.py --server.port 8501
