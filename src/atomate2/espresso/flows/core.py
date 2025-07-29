"""Core Quantum ESPRESSO flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from jobflow import Flow, Maker

from atomate2.espresso.jobs.core import BandsMaker, SCFMaker

if TYPE_CHECKING:
    from pymatgen.core.structure import Structure


@dataclass
class BandGapMaker(Maker):
    """
    Maker to calculate band gap using Quantum ESPRESSO.
    
    This workflow performs:
    1. SCF calculation to get ground state
    2. Bands calculation with denser k-points to get accurate band gap
    
    Parameters
    ----------
    name : str
        Name of the flow.
    scf_maker : SCFMaker
        Maker for the SCF calculation.
    bands_maker : BandsMaker  
        Maker for the bands calculation.
    """
    
    name: str = "quantum espresso band gap"
    scf_maker: SCFMaker = field(default_factory=SCFMaker)
    bands_maker: BandsMaker = field(default_factory=BandsMaker)
    
    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """
        Create a band gap calculation flow.
        
        Parameters
        ----------
        structure : Structure
            Pymatgen structure object.
        prev_dir : str or Path or None
            Previous calculation directory.
            
        Returns
        -------
        Flow
            A flow containing SCF and bands calculations.
        """
        # Step 1: SCF calculation
        scf_job = self.scf_maker.make(structure, prev_dir=prev_dir)
        scf_job.name = "scf calculation"
        
        # Step 2: Bands calculation using SCF results
        bands_job = self.bands_maker.make(
            scf_job.output.structure,
            prev_dir=scf_job.output.dir_name
        )
        bands_job.name = "bands calculation"
        
        # Create flow
        jobs = [scf_job, bands_job]
        
        # Output includes both calculations with band gap from bands calculation
        output = {
            "scf": scf_job.output,
            "bands": bands_job.output,
            "band_gap": bands_job.output.band_gap,
            "structure": bands_job.output.structure,
        }
        
        return Flow(jobs, output=output, name=self.name)


@dataclass
class RelaxBandGapMaker(Maker):
    """
    Maker for structure relaxation followed by band gap calculation.
    
    This workflow performs:
    1. Structure relaxation using force fields or QE relax
    2. Band gap calculation on relaxed structure
    
    Parameters
    ---------- 
    name : str
        Name of the flow.
    relax_maker : Maker
        Maker for structure relaxation.
    band_gap_maker : BandGapMaker
        Maker for band gap calculation.
    """
    
    name: str = "relax and band gap"
    relax_maker: Maker | None = None  # Could use force field relaxation
    band_gap_maker: BandGapMaker = field(default_factory=BandGapMaker)
    
    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """
        Create a relaxation + band gap flow.
        
        Parameters
        ----------
        structure : Structure
            Input structure.
        prev_dir : str or Path or None
            Previous directory.
            
        Returns
        -------
        Flow
            Flow with relaxation and band gap calculation.
        """
        jobs = []
        current_structure = structure
        current_prev_dir = prev_dir
        
        # Optional relaxation step
        if self.relax_maker:
            relax_job = self.relax_maker.make(structure, prev_dir=prev_dir)
            relax_job.name = "structure relaxation"
            jobs.append(relax_job)
            current_structure = relax_job.output.structure
            current_prev_dir = relax_job.output.dir_name
        
        # Band gap calculation
        bg_flow = self.band_gap_maker.make(current_structure, prev_dir=current_prev_dir)
        jobs.append(bg_flow)
        
        return Flow(jobs, output=bg_flow.output, name=self.name)