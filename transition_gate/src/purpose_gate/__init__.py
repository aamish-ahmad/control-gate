"""Intent Transition Gate: side-effect-free, human-authority-preserving routing."""
from .engine import Decision, decide
from .transition import Transition, advance

__all__ = ['Decision', 'decide', 'Transition', 'advance']
