#!/usr/bin/env python3
"""Debug ASE Espresso calculator configuration."""

import os
from ase import Atoms
from ase.calculators.espresso import Espresso, EspressoProfile
from pymatgen.core import Structure
from pymatgen.io.ase import AseAtomsAdaptor

def test_ase_espresso():
    """Test ASE Espresso calculator setup."""
    
    print("Testing ASE Espresso calculator setup...")
    
    # Create simple Silicon structure
    structure = Structure(
        lattice=[[0, 2.73, 2.73], [2.73, 0, 2.73], [2.73, 2.73, 0]],
        species=["Si", "Si"],
        coords=[[0, 0, 0], [0.25, 0.25, 0.25]]
    )
    
    atoms = AseAtomsAdaptor.get_atoms(structure)
    print(f"✓ Created atoms: {atoms}")
    
    # Set up profile
    profile = EspressoProfile(
        command='pw.x',
        pseudo_dir='/app/pseudopotentials'
    )
    print(f"✓ Created profile: {profile}")
    
    # Test minimal calculator setup
    try:
        calc = Espresso(
            profile=profile,
            calculation='scf',
            pseudopotentials={'Si': 'Si.pbe-n-rrkjus_psl.1.0.0.UPF'},
            kpts=(2, 2, 2),
            ecutwfc=30.0,
            conv_thr=1e-6,
        )
        print(f"✓ Created calculator: {calc}")
        
        # Try to set calculator (but not run)
        atoms.calc = calc
        print("✓ Successfully assigned calculator to atoms")
        
        # Don't actually run calculation - just test setup
        print("✅ ASE setup successful!")
        
    except Exception as e:
        print(f"❌ ASE setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ase_espresso()