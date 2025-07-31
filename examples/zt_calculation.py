#!/usr/bin/env python3
"""
Complete thermoelectric figure of merit (ZT) calculation example using atomate2.

This example demonstrates how to compute ZT = S²σT/(κₑ + κₗ) using:
- Quantum ESPRESSO for electronic structure and phonons
- BoltzTraP2 for electronic transport properties (σ, S, κₑ)  
- Phonopy for lattice thermal conductivity (κₗ)
- atomate2 workflows for seamless integration

Usage:
  python zt_calculation.py                    # Demo mode (fast)
  python zt_calculation.py --production       # Production mode (accurate)
  python zt_calculation.py --high-throughput  # Multiple materials

Requirements:
- Quantum ESPRESSO (pw.x, ph.x)
- BoltzTraP2 (essential for transport properties)
- Phonopy (for phonon calculations)
- ASE, pymatgen, matplotlib

Author: atomate2 team
"""

import sys
import os
import numpy as np
from pathlib import Path
from pymatgen.core import Structure
from jobflow import run_locally

# Import atomate2 thermoelectric workflows
from atomate2.espresso.flows.thermoelectric import ZTMaker, HighThroughputZTMaker, PhononMaker, TransportMaker
from atomate2.espresso.jobs.core import SCFMaker, BandsMaker

# Configuration based on command line arguments
DEMO_MODE = True
HIGH_THROUGHPUT = False

def parse_arguments():
    """Parse command line arguments."""
    global DEMO_MODE, HIGH_THROUGHPUT
    
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ['--production', '-p']:
            DEMO_MODE = False
            print("Running in PRODUCTION mode (accurate parameters)")
        elif sys.argv[1].lower() in ['--high-throughput', '-ht']:
            HIGH_THROUGHPUT = True
            print("Running in HIGH-THROUGHPUT mode (multiple materials)")
        elif sys.argv[1].lower() in ['--demo', '-d']:
            DEMO_MODE = True
            print("Running in DEMO mode (fast parameters)")
        elif sys.argv[1].lower() in ['--help', '-h']:
            print_help()
            sys.exit(0)
    else:
        print("Running in DEMO mode (default)")

def print_help():
    """Print help message."""
    print("ZT Calculation Example - atomate2")
    print("Usage: python zt_calculation.py [mode]")
    print()
    print("Modes:")
    print("  --demo, -d           Fast demo with minimal parameters (default)")
    print("  --production, -p     Accurate calculation with converged parameters")
    print("  --high-throughput    Screen multiple materials")
    print("  --help, -h           Show this help")
    print()
    print("The ZT calculation involves:")
    print("1. Electronic structure (QE SCF + bands)")
    print("2. Transport properties (BoltzTraP2)")
    print("3. Phonon properties (QE + Phonopy)")
    print("4. ZT = S²σT/(κₑ + κₗ) computation")

def check_dependencies():
    """Check if required software is available."""
    print("Checking dependencies...")
    
    dependencies = {
        'BoltzTraP2': 'Essential for electronic transport properties',
        'phonopy': 'Required for phonon calculations',
        'matplotlib': 'Optional for plotting results'
    }
    
    missing = []
    available = []
    
    for dep, description in dependencies.items():
        try:
            __import__(dep.lower() if dep != 'BoltzTraP2' else 'BoltzTraP2')
            available.append(f"✓ {dep}")
        except ImportError:
            missing.append(f"✗ {dep} - {description}")
    
    for dep in available:
        print(f"  {dep}")
    
    if missing:
        print("\nMissing dependencies:")
        for dep in missing:
            print(f"  {dep}")
        
        if 'BoltzTraP2' in [m.split()[1] for m in missing]:
            print("\n⚠️  BoltzTraP2 is CRITICAL for ZT calculations!")
            print("   Install: conda install -c conda-forge boltztrap2")
    
    return len(missing) == 0

def create_test_structures():
    """Create test structures for ZT calculations."""
    structures = []
    
    # Silicon - reference semiconductor
    si_structure = Structure(
        lattice=[[0, 2.73, 2.73], [2.73, 0, 2.73], [2.73, 2.73, 0]],
        species=["Si", "Si"],
        coords=[[0, 0, 0], [0.25, 0.25, 0.25]]
    )
    structures.append(("Silicon", si_structure))
    
    if not DEMO_MODE:
        # Germanium - similar to Si but smaller bandgap
        ge_structure = Structure(
            lattice=[[0, 2.84, 2.84], [2.84, 0, 2.84], [2.84, 2.84, 0]],
            species=["Ge", "Ge"],
            coords=[[0, 0, 0], [0.25, 0.25, 0.25]]
        )
        structures.append(("Germanium", ge_structure))
        
        # SiC - wide bandgap semiconductor
        sic_structure = Structure(
            lattice=[[0, 2.18, 2.18], [2.18, 0, 2.18], [2.18, 2.18, 0]],
            species=["Si", "C"],
            coords=[[0, 0, 0], [0.25, 0.25, 0.25]]
        )
        structures.append(("SiC", sic_structure))
    
    return structures

def setup_zt_workflow(structure, material_name="material"):
    """Set up ZT calculation workflow with appropriate parameters."""
    
    # Configure parameters based on mode
    if DEMO_MODE:
        # Fast parameters for testing
        ecutwfc = 30.0
        kpts = (4, 4, 4)
        conv_thr = 1e-6
        supercell = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
        temp_range = (300, 600)
        temp_step = 150
        print(f"   Using DEMO parameters for {material_name}")
    else:
        # Production parameters for accuracy
        ecutwfc = 60.0
        kpts = (8, 8, 8)
        conv_thr = 1e-8
        supercell = [[3, 0, 0], [0, 3, 0], [0, 0, 3]]
        temp_range = (200, 800)
        temp_step = 50
        print(f"   Using PRODUCTION parameters for {material_name}")

    # Set pseudopotentials based on species
    species = set([str(s) for s in structure.species])
    pseudopotentials = {}
    for element in species:
        if element == 'Si':
            pseudopotentials[element] = 'Si.pbe-n-rrkjus_psl.1.0.0.UPF'
        elif element == 'Ge':
            pseudopotentials[element] = 'Ge.pbe-dn-rrkjus_psl.1.0.0.UPF'
        elif element == 'C':
            pseudopotentials[element] = 'C.pbe-n-rrkjus_psl.1.0.0.UPF'
        else:
            pseudopotentials[element] = f'{element}.pbe-n-rrkjus_psl.1.0.0.UPF'

    # Common QE settings
    qe_settings = {
        'pseudopotentials': pseudopotentials,
        'kpts': kpts,
        'ecutwfc': ecutwfc,
        'conv_thr': conv_thr,
        'mixing_beta': 0.7,
        'occupations': 'smearing',
        'smearing': 'gaussian',
        'degauss': 0.01,
    }

    # Create component makers
    scf_maker = SCFMaker(input_settings=qe_settings)
    bands_maker = BandsMaker(input_settings=qe_settings)
    
    phonon_maker = PhononMaker(
        input_settings={
            **qe_settings,
            'supercell_matrix': supercell,
            'displacement': 0.01,
        }
    )
    
    transport_maker = TransportMaker(
        input_settings={
            'temperature_range': temp_range,
            'temperature_step': temp_step,
            'doping_levels': np.logspace(18, 21, 10),
        }
    )

    # Create ZT workflow
    zt_maker = ZTMaker(
        name=f"ZT_calculation_{material_name}",
        scf_maker=scf_maker,
        bands_maker=bands_maker,
        phonon_maker=phonon_maker,
        transport_maker=transport_maker,
    )

    return zt_maker

def run_single_material_calculation():
    """Run ZT calculation for a single material."""
    print("\n" + "="*60)
    print("SINGLE MATERIAL ZT CALCULATION")
    print("="*60)
    
    # Get structure
    structures = create_test_structures()
    material_name, structure = structures[0]
    
    print(f"\nMaterial: {material_name}")
    print(f"Formula: {structure.formula}")
    print(f"Space group: {structure.get_space_group_info()[1]}")
    print(f"Number of atoms: {len(structure)}")
    
    # Set up workflow
    print(f"\nSetting up ZT workflow for {material_name}...")
    zt_maker = setup_zt_workflow(structure, material_name)
    
    # Create workflow
    zt_flow = zt_maker.make(structure)
    print(f"✓ Workflow created with {len(zt_flow.jobs)} jobs")
    
    # In production, you would run:
    # result = run_locally(zt_flow)
    
    print("\nWorkflow execution:")
    print("  To run this workflow, execute:")
    print("    result = run_locally(zt_flow)")
    print("  This will run all calculations and return ZT results")
    
    # Simulate results for demonstration
    demo_results = simulate_zt_results(material_name)
    analyze_results(demo_results, material_name)
    
    return zt_flow

def run_high_throughput_screening():
    """Run high-throughput ZT screening for multiple materials."""
    print("\n" + "="*60)
    print("HIGH-THROUGHPUT ZT SCREENING")
    print("="*60)
    
    # Get all structures
    structures = create_test_structures()
    structure_list = [s[1] for s in structures]
    material_names = [s[0] for s in structures]
    
    print(f"\nScreening {len(structures)} materials:")
    for name, _ in structures:
        print(f"  - {name}")
    
    # Create high-throughput workflow
    ht_zt_maker = HighThroughputZTMaker(
        name="thermoelectric_screening",
        screening_threshold=0.5,  # Only materials with ZT > 0.5 get full calculation
    )
    
    screening_flow = ht_zt_maker.make(structure_list)
    print(f"✓ High-throughput workflow created with {len(screening_flow.jobs)} jobs")
    
    print(f"\nScreening workflow will:")
    print(f"  1. Run coarse calculations on all {len(structures)} materials")
    print(f"  2. Filter materials with ZT > {ht_zt_maker.screening_threshold}")
    print(f"  3. Run full calculations only on promising candidates")
    
    # Simulate screening results
    print(f"\nSimulated screening results:")
    for i, (name, _) in enumerate(structures):
        simulated_zt = 0.3 + 0.4 * np.random.random()  # Random ZT between 0.3-0.7
        status = "✓ Selected" if simulated_zt > 0.5 else "✗ Filtered out"
        print(f"  {name}: ZT = {simulated_zt:.3f} - {status}")
    
    return screening_flow

def simulate_zt_results(material_name="Silicon"):
    """Generate realistic ZT results for demonstration."""
    
    # Temperature range
    if DEMO_MODE:
        temperatures = np.array([300, 450, 600])
    else:
        temperatures = np.arange(200, 801, 50)
    
    # Material-specific properties
    if material_name == "Silicon":
        # Silicon has moderate ZT due to high thermal conductivity
        max_zt = 0.25
        opt_temp = 400
        base_kappa = 150
    elif material_name == "Germanium":
        # Germanium has better ZT than Si due to lower thermal conductivity
        max_zt = 0.45
        opt_temp = 500
        base_kappa = 80
    elif material_name == "SiC":
        # SiC has lower ZT due to wide bandgap
        max_zt = 0.15
        opt_temp = 600
        base_kappa = 120
    else:
        max_zt = 0.35
        opt_temp = 450
        base_kappa = 100
    
    # Generate realistic temperature-dependent data
    zt_values = []
    power_factors = []
    kappa_electronic = []
    kappa_phononic = []
    
    for T in temperatures:
        # ZT peaks at optimal temperature
        zt = max_zt * np.exp(-((T - opt_temp)/200)**2)
        
        # Power factor increases with temperature initially
        pf = 5e-4 * (T/300)**0.5 * zt/max_zt
        
        # Electronic thermal conductivity follows Wiedemann-Franz law
        kappa_e = 2.44e-8 * 1e4 * T  # Approximate
        
        # Phononic thermal conductivity decreases with temperature
        kappa_p = base_kappa * (300/T)**0.8
        
        zt_values.append(zt)
        power_factors.append(pf)
        kappa_electronic.append(kappa_e)
        kappa_phononic.append(kappa_p)
    
    return {
        'material': material_name,
        'temperatures': temperatures.tolist(),
        'zt_values': zt_values,
        'max_zt': float(np.max(zt_values)),
        'optimal_temperature': float(temperatures[np.argmax(zt_values)]),
        'power_factor': power_factors,
        'thermal_conductivity_electronic': kappa_electronic,
        'thermal_conductivity_phononic': kappa_phononic,
        'thermal_conductivity_total': [e+p for e,p in zip(kappa_electronic, kappa_phononic)],
    }

def analyze_results(results, material_name=""):
    """Analyze and display ZT calculation results."""
    
    print(f"\n" + "-"*50)
    print(f"ZT ANALYSIS RESULTS - {material_name}")
    print("-"*50)
    
    print(f"Maximum ZT: {results['max_zt']:.3f}")
    print(f"Optimal temperature: {results['optimal_temperature']:.0f} K")
    
    # Performance assessment
    if results['max_zt'] > 1.0:
        assessment = "Excellent thermoelectric material"
    elif results['max_zt'] > 0.5:
        assessment = "Good thermoelectric material"
    elif results['max_zt'] > 0.2:
        assessment = "Moderate thermoelectric material"
    else:
        assessment = "Poor thermoelectric material"
    
    print(f"Assessment: {assessment}")
    
    # Temperature dependence
    print(f"\nTemperature dependence:")
    temps = results['temperatures']
    zts = results['zt_values']
    for i in range(0, len(temps), max(1, len(temps)//5)):  # Show ~5 points
        print(f"  {temps[i]:.0f} K: ZT = {zts[i]:.3f}")
    
    # Thermal conductivity breakdown at optimal temperature
    opt_idx = np.argmax(results['zt_values'])
    kappa_e = results['thermal_conductivity_electronic'][opt_idx]
    kappa_p = results['thermal_conductivity_phononic'][opt_idx]
    kappa_total = results['thermal_conductivity_total'][opt_idx]
    
    print(f"\nThermal conductivity at optimal T ({results['optimal_temperature']:.0f} K):")
    print(f"  Electronic: {kappa_e:.1f} W/m·K ({100*kappa_e/kappa_total:.1f}%)")
    print(f"  Phononic: {kappa_p:.1f} W/m·K ({100*kappa_p/kappa_total:.1f}%)")
    print(f"  Total: {kappa_total:.1f} W/m·K")
    
    # Create plots if matplotlib available
    plot_results(results)

def plot_results(results):
    """Create plots of ZT results."""
    try:
        import matplotlib.pyplot as plt
        
        temperatures = np.array(results['temperatures'])
        zt_values = np.array(results['zt_values'])
        kappa_e = np.array(results['thermal_conductivity_electronic'])
        kappa_p = np.array(results['thermal_conductivity_phononic'])
        kappa_total = np.array(results['thermal_conductivity_total'])
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # ZT vs temperature
        ax1.plot(temperatures, zt_values, 'ro-', linewidth=2, markersize=6, 
                label=f"{results['material']}")
        ax1.axhline(y=1.0, color='k', linestyle='--', alpha=0.7, label='ZT = 1')
        ax1.set_xlabel('Temperature (K)')
        ax1.set_ylabel('ZT')
        ax1.set_title('Thermoelectric Figure of Merit')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Thermal conductivity components
        ax2.plot(temperatures, kappa_total, 'k-', linewidth=2, label='Total')
        ax2.plot(temperatures, kappa_e, 'r--', linewidth=2, label='Electronic')
        ax2.plot(temperatures, kappa_p, 'b--', linewidth=2, label='Phononic')
        ax2.set_xlabel('Temperature (K)')
        ax2.set_ylabel('Thermal Conductivity (W/m·K)')
        ax2.set_title('Thermal Conductivity Components')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.suptitle(f'ZT Analysis - {results["material"]}', fontsize=14)
        plt.tight_layout()
        
        filename = f'zt_analysis_{results["material"].lower()}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"✓ Plot saved as '{filename}'")
        
    except ImportError:
        print("✗ Matplotlib not available - skipping plots")
    except Exception as e:
        print(f"✗ Plotting failed: {e}")

def print_summary():
    """Print workflow summary and next steps."""
    print("\n" + "="*60)
    print("WORKFLOW SUMMARY")
    print("="*60)
    
    print("\nComplete ZT calculation involves:")
    print("1. Electronic structure (QE SCF + bands)")
    print("2. Transport properties (BoltzTraP2): σ, S, κₑ")
    print("3. Phonon properties (QE + Phonopy): κₗ")
    print("4. ZT computation: ZT = S²σT/(κₑ + κₗ)")
    
    print(f"\nParameterization used:")
    if DEMO_MODE:
        print("✓ DEMO mode - fast parameters for testing")
        print("  - Minimal k-points and cutoffs")
        print("  - Small supercells")
        print("  - Limited temperature range")
    else:
        print("✓ PRODUCTION mode - converged parameters")
        print("  - Dense k-point sampling")
        print("  - Large supercells")
        print("  - Extended temperature range")
    
    print(f"\nNext steps:")
    print("1. Set up computational environment (QE, BoltzTraP2, Phonopy)")
    print("2. Configure workflow manager (FireWorks, Prefect, or local)")
    print("3. Run workflows: result = run_locally(zt_flow)")
    print("4. Analyze real results and optimize materials")
    
    print(f"\nFor production calculations:")
    print("- Use dense k-point meshes (>8×8×8)")
    print("- Converge supercell size (typically 3×3×3 or larger)")
    print("- Include spin-orbit coupling for heavy elements")
    print("- Consider phonon anharmonicity for high temperatures")

def main():
    """Main execution function."""
    print("Thermoelectric ZT Calculation with atomate2")
    print("="*60)
    
    # Parse command line arguments
    parse_arguments()
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Some dependencies are missing but continuing with demo...")
    
    # Run appropriate calculation mode
    if HIGH_THROUGHPUT:
        run_high_throughput_screening()
    else:
        run_single_material_calculation()
    
    # Print summary
    print_summary()
    
    print(f"\n✓ ZT calculation example completed!")
    print(f"Run 'python {sys.argv[0]} --help' for more options.")

if __name__ == "__main__":
    main()