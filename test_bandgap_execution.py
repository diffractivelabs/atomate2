#!/usr/bin/env python3
"""Test actually executing the bandgap workflow."""

from pymatgen.core import Lattice, Structure
from atomate2.espresso import BandGapMaker
from jobflow import run_locally

def test_bandgap_execution():
    """Test actually running the bandgap workflow."""
    
    # Create silicon structure
    lattice = Lattice.cubic(5.43)
    species = ["Si"] * 2
    coords = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]
    structure = Structure(lattice, species, coords)
    
    print("Creating bandgap workflow...")
    bg_maker = BandGapMaker(name="Test bandgap execution")
    bg_flow = bg_maker.make(structure)
    print(f"✓ Workflow created with {len(bg_flow.jobs)} jobs")
    
    print("\n🚀 Actually executing the workflow...")
    try:
        result = run_locally(bg_flow)
        print("✅ Workflow executed successfully!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bandgap_execution()