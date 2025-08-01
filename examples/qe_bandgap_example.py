"""
Example usage of Quantum ESPRESSO band gap workflow in atomate2.

This example demonstrates how to use the new QE band gap calculation workflow
that combines SCF and bands calculations to compute accurate band gaps.
"""

from jobflow import run_locally
from pymatgen.core import Lattice, Structure

from atomate2.espresso import BandGapMaker, RelaxBandGapMaker


def create_silicon_structure():
    """Create a silicon diamond structure."""
    lattice = Lattice.cubic(5.43)  # Silicon lattice parameter in Angstroms
    species = ["Si"] * 2
    coords = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]
    return Structure(lattice, species, coords)


def main():
    """Run QE band gap calculation examples."""

    # Create silicon structure
    structure = create_silicon_structure()
    print(f"Created structure: {structure.formula}")

    # Example 1: Basic band gap calculation
    print("\n=== Example 1: Basic Band Gap Calculation ===")

    # Create band gap workflow maker
    bg_maker = BandGapMaker(
        name="Si band gap calculation"
    )

    # Generate the workflow
    bg_flow = bg_maker.make(structure)
    print(f"Created workflow: {bg_flow.name}")
    print(f"Number of jobs: {len(bg_flow.jobs)}")
    print(f"Job names: {[job.name for job in bg_flow.jobs]}")

    # Example 2: Customized band gap calculation
    print("\n=== Example 2: Customized Band Gap Calculation ===")

    # Customize SCF and bands settings
    from atomate2.espresso.jobs.core import SCFMaker, BandsMaker

    custom_scf = SCFMaker(
        name="custom scf",
        input_settings={
            'pseudopotentials': {'Si': 'Si.pbe-n-rrkjus_psl.1.0.0.UPF'},
            'kpts': (12, 12, 12),  # Denser k-points
            'ecutwfc': 60.0,       # Higher cutoff
            'conv_thr': 1e-10,     # Tighter convergence
            'mixing_beta': 0.5,
            'occupations': 'fixed',
        }
    )

    custom_bands = BandsMaker(
        name="custom bands",
        input_settings={
            'kpts': (16, 16, 16),  # Very dense k-points for bands
            'nbnd': 30,            # More bands
        }
    )

    custom_bg_maker = BandGapMaker(
        name="Custom Si band gap",
        scf_maker=custom_scf,
        bands_maker=custom_bands
    )

    custom_flow = custom_bg_maker.make(structure)
    print(f"Custom workflow: {custom_flow.name}")

    # Example 3: Relax + band gap calculation
    print("\n=== Example 3: Relaxation + Band Gap Calculation ===")

    # This would use a force field for relaxation first
    relax_bg_maker = RelaxBandGapMaker(
        name="Relax and band gap",
        # relax_maker could be added here if needed
        band_gap_maker=bg_maker
    )

    relax_flow = relax_bg_maker.make(structure)
    print(f"Relax + band gap workflow: {relax_flow.name}")

    print("\n=== Workflow Information ===")
    print("The workflows are now ready to be submitted to a job manager.")
    print("They will:")
    print("1. Run SCF calculation to get ground state")
    print("2. Run bands calculation with denser k-points")
    print("3. Extract band gap from the results")
    print("\nRequirements:")
    print("- Quantum ESPRESSO installation")
    print("- ASE with QE calculator support")
    print("- Appropriate pseudopotentials")

    result = run_locally(relax_flow)
    breakpoint()


if __name__ == "__main__":
    main()