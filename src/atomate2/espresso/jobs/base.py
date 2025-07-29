"""Base Quantum ESPRESSO job maker."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jobflow import Maker
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

if TYPE_CHECKING:
    from jobflow import Job

logger = logging.getLogger(__name__)


@dataclass
class BaseEspressoMaker(Maker, ABC):
    """
    Base Quantum ESPRESSO job maker.
    
    Parameters
    ----------
    name : str
        The job name.
    input_settings : dict
        Input settings for the QE calculation.
    """
    
    name: str = "quantum espresso job"
    input_settings: dict[str, Any] = field(default_factory=dict)
    
    @abstractmethod
    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Job:
        """Make a Quantum ESPRESSO job."""