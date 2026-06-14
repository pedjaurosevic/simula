"""simula — lokalno-prvi pogon za sazdavanje i naseljavanje svetova i persona iz korisnikovih
materijala. Vidi PLAN.md i PRINCIPLES.md.

Jedan engine, dva tipa blueprinta (world | persona), jedinstven model entiteta (Simulacrum).
"""
from .backends import Backend, Contract, Message, from_config
from .loop import Simulacrum, TurnResult, run_turn
from .workspace import bootstrap_workspace, default_workspace

__all__ = [
    "Backend", "Contract", "Message", "from_config",
    "Simulacrum", "TurnResult", "run_turn",
    "bootstrap_workspace", "default_workspace",
]
__version__ = "0.1.0"
