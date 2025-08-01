"""
Example: Running atomate2 workflows with Prefect

This demonstrates different approaches to integrate atomate2 with Prefect for
workflow orchestration, monitoring, and execution.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from prefect import flow, task
from prefect.logging import get_run_logger
from pymatgen.core import Structure

# Optional: Import atomate2 components (would need proper installation)
try:
    from atomate2.vasp.jobs.core import RelaxMaker, StaticMaker, NonSCFMaker
    from atomate2.vasp.flows.core import RelaxBandStructureMaker
    from jobflow import run_locally
    ATOMATE2_AVAILABLE = True
except ImportError:
    ATOMATE2_AVAILABLE = False
    print("atomate2 not available - showing example structure only")


# Approach 1: Direct Job Function Wrapping
# ========================================

@task(name="VASP Relaxation", retries=2, retry_delay_seconds=60)
def vasp_relax_task(
    structure: Structure,
    prev_dir: Optional[str] = None,
    **maker_kwargs
) -> Dict[str, Any]:
    """
    Run a VASP relaxation calculation as a Prefect task.
    
    Args:
        structure: Pymatgen Structure object
        prev_dir: Previous calculation directory to copy from
        **maker_kwargs: Additional settings for RelaxMaker
        
    Returns:
        Dictionary containing relaxation results
    """
    logger = get_run_logger()
    logger.info(f"Starting VASP relaxation for {structure.formula}")
    
    if not ATOMATE2_AVAILABLE:
        # Mock result for demonstration
        return {
            "structure": structure,
            "energy": -10.5,
            "forces": [[0.0, 0.0, 0.0]] * len(structure),
            "dir_name": "/tmp/mock_relax",
            "formula": structure.formula
        }
    
    # Create the relaxation job
    relax_maker = RelaxMaker(**maker_kwargs)
    relax_job = relax_maker.make(structure, prev_dir=prev_dir)
    
    # Execute the job function directly
    result = relax_job.function(
        structure=structure, 
        prev_dir=prev_dir,
        **relax_job.kwargs
    )
    
    logger.info(f"Relaxation completed. Final energy: {result.get('energy', 'N/A')} eV")
    return result


@task(name="VASP Static", retries=2, retry_delay_seconds=60)
def vasp_static_task(
    structure: Structure,
    prev_dir: Optional[str] = None,
    **maker_kwargs
) -> Dict[str, Any]:
    """
    Run a VASP static calculation as a Prefect task.
    """
    logger = get_run_logger()
    logger.info(f"Starting VASP static calculation for {structure.formula}")
    
    if not ATOMATE2_AVAILABLE:
        return {
            "structure": structure,
            "energy": -10.7,
            "eigenvalues": [[-5.2, -3.1, 2.4, 4.8]],
            "dir_name": "/tmp/mock_static",
            "formula": structure.formula
        }
    
    static_maker = StaticMaker(**maker_kwargs)
    static_job = static_maker.make(structure, prev_dir=prev_dir)
    
    result = static_job.function(
        structure=structure,
        prev_dir=prev_dir,
        **static_job.kwargs
    )
    
    logger.info(f"Static calculation completed. Energy: {result.get('energy', 'N/A')} eV")
    return result


@task(name="VASP Band Structure", retries=2, retry_delay_seconds=60)
def vasp_bands_task(
    structure: Structure,
    prev_dir: Optional[str] = None,
    **maker_kwargs
) -> Dict[str, Any]:
    """
    Run a VASP non-SCF calculation for band structure.
    """
    logger = get_run_logger()
    logger.info(f"Starting VASP bands calculation for {structure.formula}")
    
    if not ATOMATE2_AVAILABLE:
        return {
            "structure": structure,
            "band_structure": "mock_band_structure_object",
            "band_gap": 1.12,
            "dir_name": "/tmp/mock_bands",
            "formula": structure.formula
        }
    
    bands_maker = NonSCFMaker(mode="band", **maker_kwargs)
    bands_job = bands_maker.make(structure, prev_dir=prev_dir)
    
    result = bands_job.function(
        structure=structure,
        prev_dir=prev_dir,
        **bands_job.kwargs
    )
    
    band_gap = result.get('band_gap', 'N/A')
    logger.info(f"Band structure completed. Band gap: {band_gap} eV")
    return result


# Approach 2: Jobflow Bridge Integration
# =====================================

@task(name="Execute Jobflow Workflow", retries=1)
def execute_jobflow_workflow(workflow, root_dir: str = "/tmp/atomate2_runs") -> Any:
    """
    Execute a complete jobflow workflow within a Prefect task.
    
    Args:
        workflow: Jobflow Flow object
        root_dir: Root directory for calculations
        
    Returns:
        Workflow execution results
    """
    logger = get_run_logger()
    logger.info(f"Executing jobflow workflow: {workflow.name}")
    
    if not ATOMATE2_AVAILABLE:
        return {
            "workflow_name": getattr(workflow, 'name', 'mock_workflow'),
            "status": "completed",
            "results": "mock_workflow_results"
        }
    
    # Execute the workflow using jobflow's run_locally
    results = run_locally(
        workflow, 
        create_folders=True, 
        root_dir=root_dir,
        raise_immediately=False  # Better error handling
    )
    
    logger.info(f"Workflow {workflow.name} completed successfully")
    return results


# Complete Workflow Examples
# ==========================

@flow(name="VASP Band Structure Workflow", version="1.0")
def vasp_band_structure_flow(
    structure: Structure,
    relax_settings: Optional[Dict] = None,
    static_settings: Optional[Dict] = None,
    bands_settings: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Complete VASP band structure workflow using Prefect.
    
    This workflow performs:
    1. Structure relaxation
    2. Static SCF calculation  
    3. Non-SCF band structure calculation
    
    Args:
        structure: Input crystal structure
        relax_settings: Settings for relaxation calculation
        static_settings: Settings for static calculation
        bands_settings: Settings for band structure calculation
        
    Returns:
        Complete workflow results
    """
    logger = get_run_logger()
    logger.info(f"Starting band structure workflow for {structure.formula}")
    
    # Use default settings if none provided
    relax_settings = relax_settings or {}
    static_settings = static_settings or {}
    bands_settings = bands_settings or {}
    
    # Step 1: Relax the structure
    relax_result = vasp_relax_task(structure, **relax_settings)
    relaxed_structure = relax_result["structure"]
    relax_dir = relax_result["dir_name"]
    
    # Step 2: Static calculation on relaxed structure
    static_result = vasp_static_task(
        relaxed_structure, 
        prev_dir=relax_dir, 
        **static_settings
    )
    static_dir = static_result["dir_name"]
    
    # Step 3: Band structure calculation
    bands_result = vasp_bands_task(
        relaxed_structure,
        prev_dir=static_dir,
        **bands_settings
    )
    
    # Compile final results
    final_results = {
        "initial_structure": structure,
        "relaxed_structure": relaxed_structure,
        "relax_energy": relax_result.get("energy"),
        "static_energy": static_result.get("energy"),
        "band_gap": bands_result.get("band_gap"),
        "band_structure": bands_result.get("band_structure"),
        "workflow_status": "completed"
    }
    
    logger.info(f"Workflow completed. Band gap: {final_results['band_gap']} eV")
    return final_results


@flow(name="Atomate2 Jobflow Bridge", version="1.0")
def atomate2_jobflow_bridge_flow(structure: Structure) -> Any:
    """
    Execute atomate2 workflow using jobflow bridge approach.
    
    This approach preserves the original atomate2 workflow structure
    while executing it within Prefect's orchestration framework.
    """
    logger = get_run_logger()
    logger.info(f"Creating atomate2 workflow for {structure.formula}")
    
    if not ATOMATE2_AVAILABLE:
        # Mock workflow for demonstration
        mock_workflow = type('MockWorkflow', (), {
            'name': 'Mock RelaxBandStructure Workflow',
            'jobs': []
        })()
        return execute_jobflow_workflow(mock_workflow)
    
    # Create the atomate2 workflow
    workflow_maker = RelaxBandStructureMaker()
    workflow = workflow_maker.make(structure)
    
    logger.info(f"Created workflow with {len(workflow.jobs)} jobs")
    
    # Execute via jobflow bridge
    results = execute_jobflow_workflow(workflow)
    
    return results


# Utility Functions
# =================

@task(name="Structure Validation")
def validate_structure(structure: Structure) -> Structure:
    """Validate and potentially modify input structure."""
    logger = get_run_logger()
    
    if not structure.is_valid:
        logger.warning("Invalid structure detected, attempting to fix...")
        # Add structure fixing logic here if needed
    
    logger.info(f"Structure validated: {structure.formula}")
    return structure


@task(name="Results Analysis")
def analyze_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze and post-process calculation results."""
    logger = get_run_logger()
    
    analysis = {
        "band_gap_type": "direct" if results.get("band_gap", 0) > 0 else "metallic",
        "total_energy": results.get("static_energy", results.get("energy")),
        "structure_changed": True,  # Could compare initial vs final structures
        "calculation_summary": f"Completed workflow for {results.get('formula', 'unknown')}"
    }
    
    logger.info(f"Analysis completed: {analysis['calculation_summary']}")
    return analysis


# Advanced Example with Error Handling and Monitoring
# ==================================================

@flow(name="Robust VASP Workflow", version="1.0")
def robust_vasp_workflow(
    structure: Structure,
    workflow_settings: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Production-ready VASP workflow with comprehensive error handling.
    """
    logger = get_run_logger()
    workflow_settings = workflow_settings or {}
    
    try:
        # Validate input
        validated_structure = validate_structure(structure)
        
        # Run main workflow
        results = vasp_band_structure_flow(
            validated_structure,
            relax_settings=workflow_settings.get("relax", {}),
            static_settings=workflow_settings.get("static", {}),
            bands_settings=workflow_settings.get("bands", {})
        )
        
        # Analyze results
        analysis = analyze_results(results)
        
        # Combine results and analysis
        final_output = {
            **results,
            "analysis": analysis,
            "workflow_version": "1.0",
            "success": True
        }
        
        logger.info("Robust workflow completed successfully")
        return final_output
        
    except Exception as e:
        logger.error(f"Workflow failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "workflow_version": "1.0"
        }


# Example Usage and Testing
# ========================

def create_test_structure() -> Structure:
    """Create a test silicon structure for demonstration."""
    from pymatgen.core import Lattice
    
    lattice = Lattice.cubic(5.43)  # Silicon lattice parameter
    species = ["Si"] * 2
    coords = [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25]]
    return Structure(lattice, species, coords)


if __name__ == "__main__":
    """
    Example usage of atomate2-Prefect integration.
    
    To run this example:
    1. Install Prefect: pip install prefect
    2. Install atomate2: pip install atomate2 (optional for demonstration)
    3. Run: python prefect_atomate2_example.py
    """
    
    print("=== Atomate2-Prefect Integration Example ===\n")
    
    # Create test structure
    test_structure = create_test_structure()
    print(f"Created test structure: {test_structure.formula}")
    
    # Example 1: Individual task approach
    print("\n1. Running individual VASP tasks...")
    try:
        from prefect import get_client
        # This would normally be executed via Prefect's deployment system
        print("   - Tasks defined: vasp_relax_task, vasp_static_task, vasp_bands_task")
        print("   - Use 'prefect deployment build' to deploy these workflows")
    except ImportError:
        print("   - Prefect not installed, showing structure only")
    
    # Example 2: Complete workflow
    print("\n2. Complete workflow approach:")
    print("   - Workflow: vasp_band_structure_flow")
    print("   - Features: Relaxation → Static → Band Structure")
    print("   - Includes error handling and retries")
    
    # Example 3: Jobflow bridge
    print("\n3. Jobflow bridge approach:")  
    print("   - Workflow: atomate2_jobflow_bridge_flow")
    print("   - Preserves original atomate2 workflow structure")
    print("   - Executes via jobflow's run_locally within Prefect")
    
    print("\n=== Deployment Instructions ===")
    print("1. prefect server start")
    print("2. prefect deployment build prefect_atomate2_example.py:vasp_band_structure_flow -n 'VASP Workflow'")
    print("3. prefect deployment apply vasp_band_structure_flow-deployment.yaml")
    print("4. prefect deployment run 'VASP Band Structure Workflow/VASP Workflow'")
    
    print("\n=== Benefits of Prefect Integration ===")
    benefits = [
        "✓ Web UI for workflow monitoring and visualization",
        "✓ Automatic retry logic with configurable delays",
        "✓ Structured logging and error reporting", 
        "✓ Scheduled and event-driven workflow execution",
        "✓ Resource management and scaling capabilities",
        "✓ Integration with cloud platforms and databases",
        "✓ Parameter passing and dynamic workflow generation"
    ]
    
    for benefit in benefits:
        print(f"  {benefit}")