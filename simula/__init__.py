"""simula — a local-first engine for generating and inhabiting worlds and personas from the
user's own materials. See PLAN.md and PRINCIPLES.md.

One engine, two blueprint types (world | persona), one unified entity model (Simulacrum).
"""
from .backends import Backend, Contract, Message, from_config
from .loop import Simulacrum, TurnResult, run_turn
from .workspace import bootstrap_workspace, default_workspace

__all__ = [
    "Backend", "Contract", "Message", "from_config",
    "Simulacrum", "TurnResult", "run_turn",
    "bootstrap_workspace", "default_workspace",
]
__version__ = "0.1.1"
