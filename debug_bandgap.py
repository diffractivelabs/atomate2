#!/usr/bin/env python3
"""Debug bandgap workflow creation."""

from pymatgen.core import Lattice, Structure
from atomate2.espresso import BandGapMaker

def debug_bandgap():
    """Debug the bandgap workflow creation."""
    
    # Create silicon structure
    lattice = Lattice.cubic(5.43)
    species = ["Si"] * 2
    coords = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]
    structure = Structure(lattice, species, coords)
    
    print(f"Structure type: {type(structure)}")
    print(f"Structure: {structure}")
    
    # Create workflow maker
    bg_maker = BandGapMaker(name="debug bandgap")
    
    print(f"BandGap maker: {bg_maker}")
    print(f"SCF maker: {bg_maker.scf_maker}")
    print(f"Bands maker: {bg_maker.bands_maker}")
    
    # Try to create workflow
    try:
        print("Creating workflow...")
        bg_flow = bg_maker.make(structure)
        print(f"✓ Workflow created: {bg_flow}")
        print(f"  Jobs: {len(bg_flow.jobs)}")
        for i, job in enumerate(bg_flow.jobs):
            print(f"    {i+1}. {job.name} - {type(job)}")
            print(f"       Function: {job.function}")
            print(f"       Args: {job.function_args}")
    except Exception as e:
        print(f"✗ Workflow creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_bandgap()