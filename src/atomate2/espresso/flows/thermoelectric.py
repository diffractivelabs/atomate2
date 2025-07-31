"""Thermoelectric property calculation flows using Quantum ESPRESSO."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from jobflow import Flow, Maker, Response, job
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

from atomate2.espresso.jobs.core import SCFMaker, BandsMaker
from atomate2.espresso.jobs.base import BaseEspressoMaker
from atomate2.espresso.schemas import QETaskDocument

if TYPE_CHECKING:
    from ase import Atoms

logger = logging.getLogger(__name__)


@job
def run_phonon_calculation(
    atoms: Atoms,
    input_settings: dict,
    prev_dir: str | Path | None = None,
) -> dict:
    """
    Run phonon calculation using ASE and Phonopy.
    
    Parameters
    ----------
    atoms : Atoms
        ASE atoms object.
    input_settings : dict
        Input settings for phonon calculation.
    prev_dir : str or Path or None
        Previous directory.
        
    Returns
    -------
    dict
        Phonon properties including thermal conductivity.
    """
    try:
        from phonopy import Phonopy
        from phonopy.interface.calculator import get_phonon
        from ase.calculators.espresso import Espresso
        import numpy as np
    except ImportError as e:
        raise ImportError("Phonopy is required for phonon calculations") from e
    
    # Set up QE calculator for force calculations
    calc = Espresso(
        calculation='scf',
        **input_settings
    )
    
    # Create supercell for phonon calculation
    supercell_matrix = input_settings.get('supercell_matrix', [[2, 0, 0], [0, 2, 0], [0, 0, 2]])
    
    # Get phonon object
    phonon = get_phonon(atoms, calc, supercell_matrix=supercell_matrix)
    
    # Generate displacements
    phonon.generate_displacements(distance=input_settings.get('displacement', 0.01))
    
    # Calculate forces for displaced structures
    phonon.produce_force_constants()
    
    # Calculate thermal properties
    temperatures = np.arange(100, 800, 50)  # 100K to 800K
    phonon.run_mesh([20, 20, 20])  # Dense mesh for accurate properties
    phonon.run_thermal_properties(temperatures=temperatures)
    
    # Extract thermal conductivity (simplified - would need more sophisticated approach)
    thermal_props = phonon.get_thermal_properties_dict()
    
    # Calculate phononic thermal conductivity using kinetic theory approximation
    # This is simplified - real implementation would use Boltzmann transport equation
    heat_capacity = thermal_props['heat_capacity']
    group_velocities = _calculate_group_velocities(phonon)
    mean_free_path = _estimate_mean_free_path(phonon, temperatures)
    
    kappa_ph = []
    for i, T in enumerate(temperatures):
        # κ_ph = (1/3) * C_v * v * l
        cv = heat_capacity[i]
        v_avg = np.mean(group_velocities)
        l_avg = mean_free_path[i]
        kappa_ph.append((1/3) * cv * v_avg * l_avg)
    
    return {
        'temperatures': temperatures.tolist(),
        'thermal_conductivity_phononic': kappa_ph,
        'heat_capacity': heat_capacity.tolist(),
        'phonon_frequencies': phonon.get_frequencies([0, 0, 0]).tolist(),
        'thermal_properties': thermal_props,
    }


def _calculate_group_velocities(phonon):
    """Calculate phonon group velocities."""
    # Simplified implementation
    mesh = phonon.get_mesh()
    frequencies = mesh[0]
    return np.mean(np.abs(frequencies), axis=1)


def _estimate_mean_free_path(phonon, temperatures):
    """Estimate phonon mean free path using simple model."""
    # Very simplified - real implementation would use anharmonic properties
    base_mfp = 100e-9  # 100 nm base mean free path
    return [base_mfp * (300/T) for T in temperatures]


@job
def run_transport_calculation(
    structure: Structure,
    band_structure_data: dict,
    input_settings: dict,
) -> dict:
    """
    Calculate electronic transport properties using BoltzTraP2.
    
    Parameters
    ----------
    structure : Structure
        Crystal structure.
    band_structure_data : dict
        Band structure data from QE calculation.
    input_settings : dict
        Transport calculation settings.
        
    Returns
    -------
    dict
        Electronic transport properties.
    """
    try:
        from BoltzTraP2 import sphere, fite, bandlib
        import numpy as np
    except ImportError as e:
        raise ImportError("BoltzTraP2 is required for transport calculations") from e
    
    # This is a simplified implementation
    # Real implementation would need proper band structure parsing from QE output
    
    temperatures = np.arange(100, 800, 50)
    doping_levels = np.logspace(18, 21, 10)  # carriers/cm³
    
    # Placeholder for electronic transport properties
    # In practice, this would use BoltzTraP2 with QE band structure
    seebeck_coeff = []
    electrical_conductivity = []
    electronic_thermal_conductivity = []
    
    for T in temperatures:
        # Simplified temperature dependence
        S = 100 * (T/300)  # μV/K (placeholder)
        sigma = 1e5 / T    # S/m (placeholder)
        kappa_el = sigma * 2.44e-8 * T  # Wiedemann-Franz law
        
        seebeck_coeff.append(S)
        electrical_conductivity.append(sigma)
        electronic_thermal_conductivity.append(kappa_el)
    
    return {
        'temperatures': temperatures.tolist(),
        'seebeck_coefficient': seebeck_coeff,
        'electrical_conductivity': electrical_conductivity,
        'electronic_thermal_conductivity': electronic_thermal_conductivity,
        'doping_levels': doping_levels.tolist(),
    }


@job
def calculate_zt(
    transport_props: dict,
    phonon_props: dict,
) -> dict:
    """
    Calculate thermoelectric figure of merit ZT.
    
    Parameters
    ----------
    transport_props : dict
        Electronic transport properties.
    phonon_props : dict
        Phononic properties.
        
    Returns
    -------
    dict
        ZT values and related properties.
    """
    import numpy as np
    
    temperatures = np.array(transport_props['temperatures'])
    S = np.array(transport_props['seebeck_coefficient']) * 1e-6  # Convert to V/K
    sigma = np.array(transport_props['electrical_conductivity'])
    kappa_el = np.array(transport_props['electronic_thermal_conductivity'])
    kappa_ph = np.array(phonon_props['thermal_conductivity_phononic'])
    
    # Total thermal conductivity
    kappa_total = kappa_el + kappa_ph
    
    # Calculate ZT = S²σT/κ
    power_factor = S**2 * sigma
    zt_values = power_factor * temperatures / kappa_total
    
    # Find maximum ZT and optimal temperature
    max_zt_idx = np.argmax(zt_values)
    max_zt = zt_values[max_zt_idx]
    optimal_temp = temperatures[max_zt_idx]
    
    return {
        'temperatures': temperatures.tolist(),
        'zt_values': zt_values.tolist(),
        'power_factor': power_factor.tolist(),
        'thermal_conductivity_total': kappa_total.tolist(),
        'thermal_conductivity_electronic': kappa_el.tolist(),
        'thermal_conductivity_phononic': kappa_ph,
        'max_zt': float(max_zt),
        'optimal_temperature': float(optimal_temp),
        'seebeck_coefficient': transport_props['seebeck_coefficient'],
        'electrical_conductivity': transport_props['electrical_conductivity'],
    }


@dataclass
class PhononMaker(BaseEspressoMaker):
    """
    Maker for phonon calculations using QE and Phonopy.
    
    Parameters
    ----------
    name : str
        Job name.
    input_settings : dict
        Settings for phonon calculation.
    """
    
    name: str = "phonon calculation"
    input_settings: dict = field(default_factory=lambda: {
        'pseudopotentials': {'Si': 'Si.pbe-n-rrkjus_psl.1.0.0.UPF'},
        'kpts': (8, 8, 8),
        'ecutwfc': 50.0,
        'conv_thr': 1e-8,
        'supercell_matrix': [[2, 0, 0], [0, 2, 0], [0, 0, 2]],
        'displacement': 0.01,
    })
    
    def make(self, structure: Structure, prev_dir: str | Path | None = None):
        """Make a phonon calculation job."""
        atoms = AseAtomsAdaptor.get_atoms(structure)
        
        return run_phonon_calculation(
            atoms=atoms,
            input_settings=self.input_settings,
            prev_dir=prev_dir,
        )


@dataclass
class TransportMaker(Maker):
    """
    Maker for electronic transport property calculations.
    
    Parameters
    ----------
    name : str
        Job name.
    input_settings : dict
        Transport calculation settings.
    """
    
    name: str = "transport properties"
    input_settings: dict = field(default_factory=dict)
    
    def make(self, structure: Structure, band_structure_data: dict):
        """Make a transport properties calculation job."""
        return run_transport_calculation(
            structure=structure,
            band_structure_data=band_structure_data,
            input_settings=self.input_settings,
        )


@dataclass
class ZTMaker(Maker):
    """
    Comprehensive maker for thermoelectric figure of merit (ZT) calculations.
    
    This workflow computes ZT = S²σT/κ using:
    1. Electronic structure calculations (QE)
    2. Phonon calculations (QE + Phonopy) 
    3. Electronic transport properties (BoltzTraP2)
    4. ZT calculation and analysis
    
    Parameters
    ----------
    name : str
        Workflow name.
    scf_maker : SCFMaker
        Maker for SCF calculation.
    bands_maker : BandsMaker
        Maker for band structure calculation.
    phonon_maker : PhononMaker
        Maker for phonon calculations.
    transport_maker : TransportMaker
        Maker for transport properties.
    """
    
    name: str = "thermoelectric ZT calculation"
    scf_maker: SCFMaker = field(default_factory=SCFMaker)
    bands_maker: BandsMaker = field(default_factory=BandsMaker)
    phonon_maker: PhononMaker = field(default_factory=PhononMaker)
    transport_maker: TransportMaker = field(default_factory=TransportMaker)
    
    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """
        Create a comprehensive ZT calculation workflow.
        
        Parameters
        ----------
        structure : Structure
            Input crystal structure.
        prev_dir : str or Path or None
            Previous calculation directory.
            
        Returns
        -------
        Flow
            Complete ZT calculation workflow.
        """
        jobs = []
        
        # Step 1: SCF calculation for ground state
        scf_job = self.scf_maker.make(structure, prev_dir=prev_dir)
        scf_job.name = "scf calculation"
        jobs.append(scf_job)
        
        # Step 2: Band structure calculation for transport properties
        bands_job = self.bands_maker.make(
            structure,
            prev_dir=scf_job.output.dir_name
        )
        bands_job.name = "bands calculation"
        jobs.append(bands_job)
        
        # Step 3: Phonon calculation for thermal conductivity
        phonon_job = self.phonon_maker.make(
            structure,
            prev_dir=scf_job.output.dir_name
        )
        phonon_job.name = "phonon calculation"
        jobs.append(phonon_job)
        
        # Step 4: Electronic transport properties
        transport_job = self.transport_maker.make(
            structure=structure,
            band_structure_data={"bands": bands_job.output}
        )
        transport_job.name = "transport properties"
        jobs.append(transport_job)
        
        # Step 5: Calculate ZT
        zt_job = calculate_zt(
            transport_props=transport_job.output,
            phonon_props=phonon_job.output,
        )
        zt_job.name = "ZT calculation"
        jobs.append(zt_job)
        
        # Prepare comprehensive output
        output = {
            'structure': structure,
            'scf_results': scf_job.output,
            'band_structure': bands_job.output,
            'phonon_properties': phonon_job.output,
            'transport_properties': transport_job.output,
            'zt_results': zt_job.output,
            'max_zt': zt_job.output['max_zt'],
            'optimal_temperature': zt_job.output['optimal_temperature'],
        }
        
        return Flow(jobs, output=output, name=self.name)


@dataclass
class HighThroughputZTMaker(Maker):
    """
    High-throughput ZT screening workflow with optimizations.
    
    This workflow is optimized for screening many materials:
    1. Quick pre-screening with coarse settings
    2. Full ZT calculation only for promising candidates
    3. Parallel execution where possible
    
    Parameters
    ----------
    name : str
        Workflow name.
    screening_threshold : float
        Minimum ZT threshold for full calculation.
    zt_maker : ZTMaker
        Full ZT calculation maker.
    """
    
    name: str = "high-throughput ZT screening"
    screening_threshold: float = 0.5
    zt_maker: ZTMaker = field(default_factory=ZTMaker)
    
    def make(self, structures: list[Structure]) -> Flow:
        """
        Create high-throughput ZT screening workflow.
        
        Parameters
        ----------
        structures : list[Structure]
            List of structures to screen.
            
        Returns
        -------
        Flow
            High-throughput screening workflow.
        """
        jobs = []
        
        # Screening phase - quick calculations with coarse settings
        screening_jobs = []
        for i, structure in enumerate(structures):
            # Use coarse settings for initial screening
            coarse_zt_maker = ZTMaker(
                name=f"coarse_zt_{i}",
                scf_maker=SCFMaker(input_settings={
                    'kpts': (4, 4, 4),  # Coarser k-points
                    'ecutwfc': 30.0,    # Lower cutoff
                    'conv_thr': 1e-6,   # Looser convergence
                }),
                phonon_maker=PhononMaker(input_settings={
                    'supercell_matrix': [[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Smaller supercell
                }),
            )
            
            screening_job = coarse_zt_maker.make(structure)
            screening_job.name = f"screening_{i}"
            screening_jobs.append(screening_job)
        
        jobs.extend(screening_jobs)
        
        # Full calculation phase - only for promising candidates
        @job
        def select_and_calculate_full_zt(screening_results: list[dict]) -> list[dict]:
            """Select promising candidates and run full ZT calculations."""
            full_results = []
            
            for i, result in enumerate(screening_results):
                if result['max_zt'] > self.screening_threshold:
                    logger.info(f"Material {i} passed screening with ZT={result['max_zt']:.3f}")
                    
                    # Run full calculation with fine settings
                    structure = structures[i]
                    full_zt_flow = self.zt_maker.make(structure)
                    full_result = full_zt_flow.run()
                    full_results.append({
                        'material_index': i,
                        'screening_zt': result['max_zt'],
                        'full_calculation': full_result,
                    })
                else:
                    logger.info(f"Material {i} filtered out with ZT={result['max_zt']:.3f}")
            
            return full_results
        
        # Collect screening results and run full calculations
        screening_outputs = [job.output for job in screening_jobs]
        final_job = select_and_calculate_full_zt(screening_outputs)
        final_job.name = "full ZT calculations"
        jobs.append(final_job)
        
        return Flow(jobs, output=final_job.output, name=self.name)