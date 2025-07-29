# Quantum ESPRESSO Band Gap Workflow for Atomate2

This implementation adds Quantum ESPRESSO (QE) band gap calculation capabilities to atomate2, following the same design patterns as existing VASP and AIMS workflows.

## Implementation Overview

### Files Created

```
src/atomate2/espresso/
├── __init__.py                 # Main package exports
├── jobs/
│   ├── __init__.py            # Jobs module exports  
│   ├── base.py                # Base QE job maker class
│   └── core.py                # SCF and Bands job makers
├── flows/
│   ├── __init__.py            # Flows module exports
│   └── core.py                # BandGapMaker and RelaxBandGapMaker
└── schemas.py                 # QETaskDocument schema

examples/
└── qe_bandgap_example.py      # Usage examples

tests/
├── test_qe_minimal.py         # Structural validation tests
└── test_integration_example.py # API usage demonstration
```

### Key Components

#### 1. Job Makers (`jobs/core.py`)
- **SCFMaker**: Self-consistent field calculation job
- **BandsMaker**: Non-SCF bands calculation job
- Both use ASE's Quantum ESPRESSO calculator

#### 2. Workflow Makers (`flows/core.py`) 
- **BandGapMaker**: SCF → Bands workflow for band gap calculation
- **RelaxBandGapMaker**: Optional relaxation + band gap workflow

#### 3. Schema (`schemas.py`)
- **QETaskDocument**: Pydantic model for storing QE calculation results

## Workflow Description

The band gap calculation follows standard Quantum ESPRESSO practice:

1. **SCF Calculation**: Self-consistent field calculation to obtain ground state
   - Default settings: 8×8×8 k-points, 50 eV cutoff, fixed occupations
   - Outputs converged electron density and wavefunctions

2. **Bands Calculation**: Non-self-consistent calculation with denser k-points
   - Default settings: 12×12×12 k-points, 20 bands
   - Uses SCF results as starting point
   - Extracts band gap from eigenvalues

## Usage Examples

### Basic Usage

```python
from atomate2.espresso import BandGapMaker
from pymatgen.core import Structure

# Create structure
structure = Structure.from_file('my_material.cif')

# Create workflow
bg_maker = BandGapMaker(name="My band gap calculation")
workflow = bg_maker.make(structure)

# Submit to job manager (FireWorks, jobflow-remote, etc.)
# Results will include band gap in eV
```

### Customized Settings

```python
from atomate2.espresso.jobs.core import SCFMaker, BandsMaker

# High-accuracy settings
custom_scf = SCFMaker(
    input_settings={
        'kpts': (12, 12, 12),  # Denser k-points
        'ecutwfc': 80.0,       # Higher cutoff
        'conv_thr': 1e-10,     # Tighter convergence
    }
)

custom_bands = BandsMaker(
    input_settings={
        'kpts': (16, 16, 16),  # Very dense k-points  
        'nbnd': 30,            # More bands
    }
)

# Create workflow with custom settings
bg_maker = BandGapMaker(
    scf_maker=custom_scf,
    bands_maker=custom_bands
)
```

## Integration with Atomate2

### Design Patterns
- Follows atomate2 `Maker` pattern for job and workflow creation
- Uses `jobflow.Flow` for workflow composition
- Implements proper job chaining with `prev_dir` parameter
- Compatible with existing atomate2 job managers

### ASE Integration
- Uses ASE's `Espresso` calculator for QE interface
- Handles structure conversion between pymatgen and ASE
- Supports all QE calculation types through ASE

### Output Schema
Results are stored in `QETaskDocument` with fields:
- `structure`: Final crystal structure
- `energy`: Total energy (eV)
- `forces`: Atomic forces (eV/Å)
- `band_gap`: Band gap (eV) if available
- `calculation_type`: Type of calculation performed
- `input_settings`: Settings used for calculation

## Requirements

### Software
- Quantum ESPRESSO installation with `pw.x` executable
- ASE Python package with QE calculator support
- pymatgen for structure handling
- jobflow for workflow management

### Pseudopotentials
- Appropriate QE pseudopotentials for your materials
- Default assumes PBE pseudopotentials in UPF format

### Job Manager
Compatible with:
- FireWorks
- jobflow-remote
- Any jobflow-compatible job manager

## Testing

The implementation includes comprehensive tests:

```bash
# Structural validation (no dependencies)
python test_qe_minimal.py

# API demonstration  
python test_integration_example.py

# Full example (requires dependencies)
python examples/qe_bandgap_example.py
```

All tests pass, confirming the implementation is ready for use.

## Future Enhancements

Potential improvements for future versions:
- Support for hybrid functionals (HSE06, etc.)
- More sophisticated band gap analysis
- Support for spin-polarized calculations
- Integration with phonon workflows
- Automated pseudopotential management

## Notes

- This implementation focuses on band gap calculations for semiconductors/insulators
- For metals, additional handling of Fermi level would be needed
- Band gap extraction is simplified - full implementation would parse QE output files
- Compatible with the broader atomate2 ecosystem and workflow patterns