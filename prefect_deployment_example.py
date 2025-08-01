"""
Prefect Deployment Script for Atomate2 Workflows

This script shows how to deploy atomate2 workflows to Prefect Cloud or Server
for production use with scheduling, monitoring, and resource management.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json

from prefect import flow
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule
from prefect.infrastructure import DockerContainer, Process
from prefect.filesystems import LocalFileSystem

# Import our atomate2-Prefect workflows
from prefect_atomate2_example import (
    vasp_band_structure_flow,
    atomate2_jobflow_bridge_flow,
    robust_vasp_workflow,
    create_test_structure
)


# Configuration Templates
# =======================

VASP_WORKFLOW_CONFIG = {
    "relax": {
        "input_set_generator": {
            "user_incar_settings": {
                "ENCUT": 520,
                "EDIFF": 1e-6,
                "PREC": "Accurate"
            }
        }
    },
    "static": {
        "input_set_generator": {
            "user_incar_settings": {
                "ENCUT": 520,
                "EDIFF": 1e-7,
                "PREC": "Accurate",
                "LORBIT": 11
            }
        }
    },
    "bands": {
        "input_set_generator": {
            "user_incar_settings": {
                "ENCUT": 520,
                "EDIFF": 1e-7,
                "PREC": "Accurate",
                "LORBIT": 11,
                "ICHARG": 11
            }
        }
    }
}

COMPUTE_RESOURCES = {
    "nodes": 1,
    "ntasks": 24,
    "time": "02:00:00",
    "partition": "compute",
    "memory": "64GB"
}


# Parameterized Workflows for Deployment
# ======================================

@flow(name="Production VASP Band Structure")
def production_vasp_workflow(
    structure_file: str,
    material_id: str,
    workflow_config: Optional[Dict] = None,
    output_dir: Optional[str] = None,
    notify_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Production-ready VASP workflow with file I/O and notifications.
    
    Args:
        structure_file: Path to structure file (CIF, POSCAR, etc.)
        material_id: Unique identifier for the material
        workflow_config: Custom workflow settings
        output_dir: Directory to save results
        notify_email: Email for completion notifications
    """
    from prefect.logging import get_run_logger
    from pymatgen.core import Structure
    
    logger = get_run_logger()
    logger.info(f"Starting production workflow for material {material_id}")
    
    # Load structure from file
    try:
        structure = Structure.from_file(structure_file)
        logger.info(f"Loaded structure: {structure.formula}")
    except Exception as e:
        logger.error(f"Failed to load structure from {structure_file}: {e}")
        return {"success": False, "error": f"Structure loading failed: {e}"}
    
    # Use provided config or default
    config = workflow_config or VASP_WORKFLOW_CONFIG
    
    # Set up output directory
    if output_dir:
        output_path = Path(output_dir) / material_id
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Results will be saved to: {output_path}")
    
    # Run the workflow
    try:
        results = robust_vasp_workflow(structure, config)
        
        # Save results if output directory specified
        if output_dir:
            results_file = output_path / "workflow_results.json"
            with open(results_file, 'w') as f:
                # Convert non-serializable objects to strings for JSON
                serializable_results = {
                    k: str(v) if hasattr(v, '__dict__') else v 
                    for k, v in results.items()
                }
                json.dump(serializable_results, f, indent=2)
            logger.info(f"Results saved to {results_file}")
        
        # Add metadata
        results.update({
            "material_id": material_id,
            "structure_file": structure_file,
            "output_directory": str(output_path) if output_dir else None,
            "workflow_type": "production_vasp_band_structure"
        })
        
        logger.info(f"Production workflow completed for {material_id}")
        return results
        
    except Exception as e:
        logger.error(f"Workflow failed for {material_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "material_id": material_id,
            "structure_file": structure_file
        }


@flow(name="Batch Materials Screening")
def batch_materials_workflow(
    materials_list: list,
    workflow_config: Optional[Dict] = None,
    max_concurrent: int = 5
) -> Dict[str, Any]:
    """
    Process multiple materials in parallel with concurrency control.
    
    Args:
        materials_list: List of dicts with 'structure_file' and 'material_id'
        workflow_config: Workflow settings to apply to all materials
        max_concurrent: Maximum number of concurrent workflows
    """
    from prefect.logging import get_run_logger
    from prefect.task_runners import ConcurrentTaskRunner
    
    logger = get_run_logger()
    logger.info(f"Starting batch workflow for {len(materials_list)} materials")
    
    results = {}
    config = workflow_config or VASP_WORKFLOW_CONFIG
    
    # Process materials with concurrency control
    with ConcurrentTaskRunner(max_workers=max_concurrent):
        for material in materials_list:
            material_id = material["material_id"]
            structure_file = material["structure_file"]
            
            logger.info(f"Submitting workflow for {material_id}")
            
            try:
                result = production_vasp_workflow(
                    structure_file=structure_file,
                    material_id=material_id,
                    workflow_config=config,
                    output_dir=material.get("output_dir")
                )
                results[material_id] = result
                
            except Exception as e:
                logger.error(f"Failed to process {material_id}: {e}")
                results[material_id] = {
                    "success": False,
                    "error": str(e),
                    "material_id": material_id
                }
    
    # Summary statistics
    successful = sum(1 for r in results.values() if r.get("success", True))
    failed = len(results) - successful
    
    summary = {
        "total_materials": len(materials_list),
        "successful": successful,
        "failed": failed,
        "success_rate": successful / len(materials_list) if materials_list else 0,
        "results": results
    }
    
    logger.info(f"Batch workflow completed: {successful}/{len(materials_list)} successful")
    return summary


# Deployment Configurations
# =========================

def create_local_deployment():
    """Create a local deployment for development and testing."""
    
    deployment = Deployment.build_from_flow(
        flow=production_vasp_workflow,
        name="vasp-local-dev",
        version="1.0.0",
        description="Local VASP workflow for development",
        tags=["atomate2", "vasp", "development"],
        parameters={
            "structure_file": "examples/Si.cif",
            "material_id": "Si_test",
            "workflow_config": VASP_WORKFLOW_CONFIG
        },
        infrastructure=Process(),
        work_pool_name="default-agent-pool"
    )
    
    return deployment


def create_docker_deployment():
    """Create a Docker deployment for containerized execution."""
    
    # Define Docker container with required dependencies
    docker_container = DockerContainer(
        image="materialsproject/atomate2:latest",  # Hypothetical image
        env={
            "VASP_PP_PATH": "/opt/vasp/potentials",
            "VASP_COMMAND": "mpirun -np 24 vasp_std",
            "OMP_NUM_THREADS": "1"
        },
        volumes=[
            "/data/vasp_potentials:/opt/vasp/potentials:ro",
            "/data/calculations:/tmp/calculations:rw"
        ]
    )
    
    deployment = Deployment.build_from_flow(
        flow=production_vasp_workflow,
        name="vasp-docker-production",
        version="1.0.0",
        description="Dockerized VASP workflow for production",
        tags=["atomate2", "vasp", "production", "docker"],
        infrastructure=docker_container,
        work_pool_name="docker-pool"
    )
    
    return deployment


def create_scheduled_deployment():
    """Create a scheduled deployment for regular batch processing."""
    
    # Schedule to run every day at 2 AM
    schedule = CronSchedule(cron="0 2 * * *", timezone="UTC")
    
    deployment = Deployment.build_from_flow(
        flow=batch_materials_workflow,
        name="daily-materials-screening",
        version="1.0.0",
        description="Daily batch processing of materials queue",
        tags=["atomate2", "batch", "scheduled"],
        schedule=schedule,
        parameters={
            "materials_list": [
                {
                    "structure_file": "/data/queue/material_1.cif",
                    "material_id": "mp-1001",
                    "output_dir": "/data/results"
                }
            ],
            "max_concurrent": 3
        },
        infrastructure=Process()
    )
    
    return deployment


# Monitoring and Alerting
# =======================

@flow(name="Workflow Health Check")
def workflow_health_check() -> Dict[str, Any]:
    """
    Health check for atomate2-Prefect infrastructure.
    """
    from prefect.logging import get_run_logger
    import subprocess
    
    logger = get_run_logger()
    health_status = {}
    
    # Check VASP availability
    try:
        result = subprocess.run(["vasp_std", "--version"], 
                              capture_output=True, text=True, timeout=10)
        health_status["vasp"] = "available" if result.returncode == 0 else "error"
    except:
        health_status["vasp"] = "not_found"
    
    # Check disk space
    try:
        result = subprocess.run(["df", "-h", "/tmp"], 
                              capture_output=True, text=True)
        health_status["disk_space"] = result.stdout.split('\n')[1].split()[3]
    except:
        health_status["disk_space"] = "unknown"
    
    # Check atomate2 import
    try:
        import atomate2
        health_status["atomate2"] = f"v{atomate2.__version__}"
    except ImportError:
        health_status["atomate2"] = "not_available"
    
    # Overall status
    health_status["overall"] = "healthy" if all(
        status not in ["error", "not_found", "not_available"] 
        for status in health_status.values()
    ) else "unhealthy"
    
    logger.info(f"Health check completed: {health_status['overall']}")
    return health_status


# CLI for Deployment Management
# ============================

def deploy_all():
    """Deploy all workflow configurations."""
    
    print("Deploying atomate2-Prefect workflows...")
    
    deployments = [
        ("local", create_local_deployment()),
        ("docker", create_docker_deployment()),
        ("scheduled", create_scheduled_deployment())
    ]
    
    for name, deployment in deployments:
        try:
            deployment.apply()
            print(f"✓ {name} deployment created successfully")
        except Exception as e:
            print(f"✗ {name} deployment failed: {e}")
    
    print("\nDeployment completed. Use 'prefect deployment ls' to view all deployments.")


def run_example():
    """Run a simple example workflow locally."""
    
    print("Running example atomate2-Prefect workflow...")
    
    # Create test structure
    structure = create_test_structure()
    
    # Save structure to temporary file
    structure_file = "/tmp/Si_test.cif"
    structure.to(structure_file)
    
    # Run workflow
    result = production_vasp_workflow(
        structure_file=structure_file,
        material_id="Si_example",
        output_dir="/tmp/prefect_results"
    )
    
    print(f"Workflow result: {result.get('workflow_status', 'unknown')}")
    if result.get('band_gap'):
        print(f"Band gap: {result['band_gap']} eV")


if __name__ == "__main__":
    """
    Deployment and testing script.
    
    Usage:
    python prefect_deployment_example.py deploy  # Deploy all workflows
    python prefect_deployment_example.py test    # Run test workflow
    python prefect_deployment_example.py health  # Run health check
    """
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "deploy":
            deploy_all()
        elif command == "test":
            run_example()
        elif command == "health":
            result = workflow_health_check()
            print(f"Health check result: {result}")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: deploy, test, health")
    else:
        print("=== Atomate2-Prefect Deployment Guide ===\n")
        
        print("1. Setup:")
        print("   pip install prefect atomate2")
        print("   prefect server start")
        print()
        
        print("2. Deploy workflows:")
        print("   python prefect_deployment_example.py deploy")
        print()
        
        print("3. Start worker:")
        print("   prefect worker start --pool default-agent-pool")
        print()
        
        print("4. Monitor workflows:")
        print("   Open http://localhost:4200 in browser")
        print()
        
        print("5. Trigger workflow:")
        print("   prefect deployment run 'Production VASP Band Structure/vasp-local-dev'")
        print()
        
        print("Available commands:")
        print("   python prefect_deployment_example.py deploy")
        print("   python prefect_deployment_example.py test")
        print("   python prefect_deployment_example.py health")