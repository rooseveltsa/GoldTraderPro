"""Vercel serverless entry point para o GoldTrader Pro API."""

import sys
from pathlib import Path

# Adicionar o diretorio raiz ao path para imports funcionarem
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from packages.api.main import app  # noqa: E402, F401
