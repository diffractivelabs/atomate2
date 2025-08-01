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
    
    print("\nExecuting ZT workflow...")
    print("This will run:")
    for i, job in enumerate(zt_flow.jobs, 1):
        print(f"  {i}. {job.name}")
    
    # Run the actual workflow
    print("\n🚀 Starting workflow execution...")
    result = run_locally(zt_flow)
    
    # Check if workflow actually succeeded
    if result is None:
        print("❌ Workflow returned None - execution failed")
        return None
    
    print("✅ Workflow completed successfully!")
    
    # Analyze real results
    analyze_results(result, material_name)
    
    return result

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
    
    print(f"\n🚀 Starting high-throughput screening...")
    screening_results = run_locally(screening_flow)
    
    if screening_results is None:
        print("❌ High-throughput screening failed - returned None")
        return None
        
    print("✅ High-throughput screening completed!")
    
    # Analyze screening results
    print(f"\nScreening results:")
    if isinstance(screening_results, list):
        for i, result in enumerate(screening_results):
            name = material_names[i] if i < len(material_names) else f"Material_{i}"
            if isinstance(result, dict) and 'max_zt' in result:
                zt_val = result['max_zt']
                status = "✓ Selected" if zt_val > ht_zt_maker.screening_threshold else "✗ Filtered out"
                print(f"  {name}: ZT = {zt_val:.3f} - {status}")
    
    return screening_results


def analyze_results(results, material_name=""):
    """Analyze and display ZT calculation results."""
    
    print(f"\n" + "-"*50)
    print(f"ZT ANALYSIS RESULTS - {material_name}")
    print("-"*50)
    
    # Handle workflow results
    if isinstance(results, dict) and 'zt_results' in results:
        # Real workflow results
        zt_data = results['zt_results']
        print("✅ Results from actual ZT workflow calculation")
        
        print(f"Maximum ZT: {zt_data['max_zt']:.3f}")
        print(f"Optimal temperature: {zt_data['optimal_temperature']:.0f} K")
    else:
        print("❌ Unable to parse results - unexpected result format")
        print(f"Result type: {type(results)}")
        if isinstance(results, dict):
            print(f"Available keys: {list(results.keys())}")
        return
    
    # Performance assessment
    if zt_data['max_zt'] > 1.0:
        assessment = "Excellent thermoelectric material"
    elif zt_data['max_zt'] > 0.5:
        assessment = "Good thermoelectric material"
    elif zt_data['max_zt'] > 0.2:
        assessment = "Moderate thermoelectric material"
    else:
        assessment = "Poor thermoelectric material"
    
    print(f"Assessment: {assessment}")
    
    # Temperature dependence
    print(f"\nTemperature dependence:")
    temps = zt_data['temperatures']
    zts = zt_data['zt_values']
    for i in range(0, len(temps), max(1, len(temps)//5)):  # Show ~5 points
        print(f"  {temps[i]:.0f} K: ZT = {zts[i]:.3f}")
    
    # Thermal conductivity breakdown at optimal temperature
    opt_idx = np.argmax(zt_data['zt_values'])
    kappa_e = zt_data['thermal_conductivity_electronic'][opt_idx]
    kappa_p = zt_data['thermal_conductivity_phononic'][opt_idx]
    kappa_total = zt_data['thermal_conductivity_total'][opt_idx]
    
    print(f"\nThermal conductivity at optimal T ({zt_data['optimal_temperature']:.0f} K):")
    print(f"  Electronic: {kappa_e:.1f} W/m·K ({100*kappa_e/kappa_total:.1f}%)")
    print(f"  Phononic: {kappa_p:.1f} W/m·K ({100*kappa_p/kappa_total:.1f}%)")
    print(f"  Total: {kappa_total:.1f} W/m·K")
    
    # Create plots if matplotlib available
    plot_results(zt_data)

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

def setup_ase_configuration():
    """Set up ASE configuration for Quantum ESPRESSO."""
    
    # Create ASE configuration file
    try:
        ase_config_dir = os.path.expanduser("~/.config/ase")
        os.makedirs(ase_config_dir, exist_ok=True)
        
        config_file = os.path.join(ase_config_dir, "config.ini")
        with open(config_file, 'w') as f:
            f.write("[espresso]\n")
            f.write("command = pw.x\n")
            f.write("pseudo_dir = /app/pseudopotentials\n")
        
        print(f"✓ Created ASE configuration: {config_file}")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not create ASE configuration: {e}")
        return False

def main():
    """Main execution function."""
    print("Thermoelectric ZT Calculation with atomate2")
    print("="*60)
    print("🔬 This will attempt ACTUAL ZT calculations using:")
    print("   - Quantum ESPRESSO for electronic structure")
    print("   - BoltzTraP2 for transport properties")  
    print("   - Phonopy for phonon calculations")
    print("   - atomate2 workflows for integration")
    print("")
    print("📝 Note: If QE configuration fails, workflow will stop with error")
    print("")
    
    # Parse command line arguments
    parse_arguments()
    
    # Set up ASE configuration
    print("Setting up ASE configuration...")
    setup_ase_configuration()
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Some dependencies are missing but continuing...")
        print("   Workflow execution may fail without proper setup")
    
    # Run appropriate calculation mode
    if HIGH_THROUGHPUT:
        result = run_high_throughput_screening()
    else:
        result = run_single_material_calculation()
    
    # Print summary only if we have results
    if result is not None:
        print_summary()
    else:
        print("\n❌ Workflow execution failed - no results to analyze")
        print("   Check the error messages above for details")
    
    print(f"\n✓ ZT calculation example completed!")
    print(f"Run 'python {sys.argv[0]} --help' for more options.")

if __name__ == "__main__":
    main()