"""Schemas for Quantum ESPRESSO calculations."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field
from pymatgen.core import Structure


class QETaskDocument(BaseModel):
    """
    Task document for Quantum ESPRESSO calculations.
    
    Parameters
    ----------
    structure : Structure
        The pymatgen structure.
    energy : float
        Total energy in eV.
    forces : list
        Forces on atoms.
    band_gap : float or None
        Band gap in eV if available.
    calculation_type : str
        Type of calculation performed.
    input_settings : dict
        Input settings used.
    """
    
    structure: Structure = Field(..., description="The structure used in the calculation")
    energy: float = Field(..., description="Total energy in eV")
    forces: list[list[float]] = Field(..., description="Forces on atoms in eV/Å")
    band_gap: Optional[float] = Field(None, description="Band gap in eV")
    calculation_type: str = Field(..., description="Type of calculation")
    input_settings: dict[str, Any] = Field(..., description="Input settings")
    dir_name: Optional[str] = Field(None, description="Directory name")
    
    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True