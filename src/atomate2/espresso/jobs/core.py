"""Core Quantum ESPRESSO job makers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jobflow import Job, job
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

from atomate2.espresso.jobs.base import BaseEspressoMaker
from atomate2.espresso.schemas import QETaskDocument

if TYPE_CHECKING:
    from ase import Atoms

logger = logging.getLogger(__name__)


@job
def run_qe_calculation(
    atoms: Atoms,
    calculation_type: str,
    input_settings: dict[str, Any],
    prev_dir: str | Path | None = None,
) -> QETaskDocument:
    """
    Run a Quantum ESPRESSO calculation using ASE.
    
    Parameters
    ----------
    atoms : Atoms
        ASE atoms object.
    calculation_type : str
        Type of calculation ('scf', 'nscf', 'bands').
    input_settings : dict
        Input settings for the calculation.
    prev_dir : str or Path or None
        Previous directory for file copying.
        
    Returns
    -------
    QETaskDocument
        Task document with calculation results.
    """
    from ase.calculators.espresso import Espresso, EspressoProfile
    import numpy as np
    import os
    
    # Set up ASE profile similar to the working QE script
    profile = EspressoProfile(
        command='pw.x',
        pseudo_dir=os.environ.get('ESPRESSO_PSEUDO', '/app/pseudopotentials')
    )
    
    # Set up calculator with explicit profile and input_data structure
    input_data = {
        'calculation': calculation_type,
        'verbosity': 'high',
        'restart_mode': 'from_scratch',
        'tstress': True,
        'tprnfor': True,
    }
    
    # Add settings from input_settings, handling special cases
    for key, value in input_settings.items():
        if key in ['kpts', 'pseudopotentials']:
            continue  # Handle these separately
        input_data[key] = value
    
    calc = Espresso(
        profile=profile,
        pseudopotentials=input_settings.get('pseudopotentials', {}),
        input_data=input_data,
        kpts=input_settings.get('kpts', (8, 8, 8))
    )
    
    # Run calculation
    atoms.calc = calc
    energy = atoms.get_potential_energy()
    forces = atoms.get_forces()
    
    # Extract band gap if available
    band_gap = None
    if hasattr(calc, 'results') and 'eigenvalues' in calc.results:
        eigenvalues = calc.results['eigenvalues']
        # Simple band gap calculation for non-metals
        if eigenvalues is not None:
            # This is a simplified approach - in practice you'd need more sophisticated
            # band gap analysis from the QE output
            homo_lumo = _extract_band_gap(eigenvalues)
            if homo_lumo:
                band_gap = homo_lumo
    
    # Convert back to pymatgen structure
    structure = AseAtomsAdaptor.get_structure(atoms)
    
    return QETaskDocument(
        structure=structure,
        energy=energy,
        forces=forces,
        band_gap=band_gap,
        calculation_type=calculation_type,
        input_settings=input_settings,
    )


def _extract_band_gap(eigenvalues):
    """Extract band gap from eigenvalues (simplified implementation)."""
    # This is a placeholder - real implementation would parse QE output files
    # to get accurate band gap information
    return None


@dataclass
class SCFMaker(BaseEspressoMaker):
    """
    Maker for self-consistent field calculations.
    
    Parameters
    ----------
    name : str
        The job name.
    input_settings : dict
        Settings for the SCF calculation.
    """
    
    name: str = "scf"
    input_settings: dict[str, Any] = field(default_factory=lambda: {
        'pseudopotentials': {'Si': 'Si.pbe-n-rrkjus_psl.1.0.0.UPF'},
        'kpts': (8, 8, 8),
        'ecutwfc': 50.0,
        'conv_thr': 1e-8,
        'mixing_beta': 0.7,
        'occupations': 'fixed',
    })
    
    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Job:
        """Make an SCF job."""
        atoms = AseAtomsAdaptor.get_atoms(structure)
        
        return run_qe_calculation(
            atoms=atoms,
            calculation_type='scf',
            input_settings=self.input_settings,
            prev_dir=prev_dir,
        )


@dataclass
class BandsMaker(BaseEspressoMaker):
    """
    Maker for band structure calculations (non-SCF).
    
    Parameters
    ----------
    name : str
        The job name.
    input_settings : dict
        Settings for the bands calculation.
    """
    
    name: str = "bands"
    input_settings: dict[str, Any] = field(default_factory=lambda: {
        'kpts': (12, 12, 12),  # Denser k-point grid for bands
        'nbnd': 20,  # Number of bands to calculate
    })
    
    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Job:
        """Make a bands calculation job."""
        atoms = AseAtomsAdaptor.get_atoms(structure)
        
        # Bands calculation requires previous SCF results
        bands_settings = {
            **self.input_settings,
            'calculation': 'bands'
        }
        
        return run_qe_calculation(
            atoms=atoms,
            calculation_type='bands',
            input_settings=bands_settings,
            prev_dir=prev_dir,
        )