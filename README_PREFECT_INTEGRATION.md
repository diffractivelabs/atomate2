# Atomate2-Prefect Integration

This directory contains examples and tools for running atomate2 workflows using Prefect for orchestration, monitoring, and scaling.

## Overview

**atomate2** is built on jobflow for workflow management, but you can also run atomate2 workflows using **Prefect** to gain additional benefits:

- 🎯 **Enhanced Monitoring**: Web UI with real-time workflow visualization
- 🔄 **Automatic Retries**: Configurable retry logic with exponential backoff
- 📅 **Flexible Scheduling**: Cron-based and event-driven workflow execution
- 🚀 **Scalability**: Dynamic resource allocation and cloud deployment
- 📊 **Analytics**: Built-in metrics and performance tracking
- 🔔 **Notifications**: Email/Slack alerts for workflow status

## Files

- `prefect_atomate2_example.py` - Core integration examples and workflow definitions
- `prefect_deployment_example.py` - Production deployment configurations and management
- `prefect_config.yaml` - Configuration file for various deployment scenarios
- `README_PREFECT_INTEGRATION.md` - This documentation file

## Quick Start

### 1. Installation

```bash
# Install required packages
pip install prefect atomate2 pymatgen

# Start Prefect server (in separate terminal)
prefect server start
```

### 2. Basic Example

```python
from prefect import flow, task
from pymatgen.core import Structure, Lattice
from atomate2.vasp.jobs.core import RelaxMaker

@task
def vasp_relax_task(structure):
    """Run VASP relaxation as Prefect task."""
    maker = RelaxMaker()
    job = maker.make(structure)
    return job.function(structure, **job.kwargs)

@flow
def simple_workflow():
    """Simple atomate2-Prefect workflow."""
    # Create silicon structure
    lattice = Lattice.cubic(5.43)
    structure = Structure(lattice, ["Si"]*2, [[0,0,0], [0.25,0.25,0.25]])
    
    # Run calculation
    result = vasp_relax_task(structure)
    return result

# Execute locally
if __name__ == "__main__":
    result = simple_workflow()
```

### 3. Running the Examples

```bash
# Test the example workflows
python prefect_atomate2_example.py

# Deploy to Prefect server
python prefect_deployment_example.py deploy

# Run health check
python prefect_deployment_example.py health

# Test production workflow
python prefect_deployment_example.py test
```

## Integration Approaches

### Approach 1: Direct Task Wrapping

Convert individual atomate2 jobs into Prefect tasks:

```python
@task(retries=2, retry_delay_seconds=60)
def vasp_static_task(structure, prev_dir=None, **settings):
    from atomate2.vasp.jobs.core import StaticMaker
    maker = StaticMaker(**settings)
    job = maker.make(structure, prev_dir=prev_dir)
    return job.function(structure, prev_dir=prev_dir, **job.kwargs)
```

**Pros**: Fine-grained control, native Prefect features
**Cons**: More code, loses some atomate2 abstractions

### Approach 2: Jobflow Bridge

Execute complete atomate2 workflows within Prefect tasks:

```python
@task
def execute_atomate2_workflow(workflow):
    from jobflow import run_locally
    return run_locally(workflow, create_folders=True)

@flow
def bridge_workflow(structure):
    from atomate2.vasp.flows.core import RelaxBandStructureMaker
    workflow = RelaxBandStructureMaker().make(structure)
    return execute_atomate2_workflow(workflow)
```

**Pros**: Preserves atomate2 workflow structure, minimal code changes
**Cons**: Less granular monitoring, single point of failure

### Approach 3: Hybrid Approach

Combine both methods for optimal balance:

```python
@flow
def hybrid_workflow(structure):
    # Use jobflow for complex multi-step calculations  
    phonon_workflow = PhononMaker().make(structure)
    phonon_result = execute_atomate2_workflow(phonon_workflow)
    
    # Use direct tasks for simple post-processing
    analysis = analyze_phonons_task(phonon_result)
    plot = create_plots_task(analysis)
    
    return {"phonon_data": phonon_result, "analysis": analysis, "plots": plot}
```

## Production Deployment

### 1. Local Development

```bash
# Deploy for local testing
python prefect_deployment_example.py deploy

# Start worker
prefect worker start --pool default-agent-pool
```

### 2. Docker Deployment

```python
# Configure Docker infrastructure
docker_container = DockerContainer(
    image="materialsproject/atomate2:latest",
    env={"VASP_PP_PATH": "/opt/vasp/potentials"},
    volumes=["/data/potentials:/opt/vasp/potentials:ro"]
)

deployment = Deployment.build_from_flow(
    flow=production_vasp_workflow,
    infrastructure=docker_container
)
```

### 3. Kubernetes/Cloud Deployment

```yaml
# kubernetes-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prefect-atomate2-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: worker
        image: materialsproject/atomate2:latest
        command: ["prefect", "worker", "start", "--pool", "k8s-pool"]
        resources:
          requests:
            memory: "8Gi"
            cpu: "4"
          limits:
            memory: "16Gi" 
            cpu: "8"
```

## Workflow Examples

### VASP Band Structure Workflow

```python
@flow
def vasp_band_structure_flow(structure):
    """Complete VASP band structure calculation."""
    # Step 1: Relax structure
    relax_result = vasp_relax_task(structure)
    
    # Step 2: Static SCF calculation
    static_result = vasp_static_task(
        relax_result["structure"], 
        prev_dir=relax_result["dir_name"]
    )
    
    # Step 3: Band structure calculation
    bands_result = vasp_bands_task(
        static_result["structure"],
        prev_dir=static_result["dir_name"]
    )
    
    return {
        "band_gap": bands_result["band_gap"],
        "band_structure": bands_result["band_structure"]
    }
```

### Batch Materials Screening

```python
@flow
def batch_screening_flow(materials_list):
    """Process multiple materials in parallel."""
    results = {}
    
    for material in materials_list:
        structure = Structure.from_file(material["structure_file"])
        result = vasp_band_structure_flow(structure)
        results[material["id"]] = result
    
    return results
```

### Adaptive Workflows

```python
@flow
def adaptive_workflow(structure):
    """Workflow that adapts based on intermediate results."""
    # Initial calculation
    initial_result = vasp_static_task(structure)
    
    # Adapt based on band gap
    if initial_result["band_gap"] < 0.1:  # Metallic
        # Run more detailed electronic structure analysis
        dos_result = vasp_dos_task(structure, prev_dir=initial_result["dir_name"])
        return {"type": "metallic", "dos": dos_result}
    else:  # Semiconducting
        # Run optical properties calculation
        optics_result = vasp_optics_task(structure, prev_dir=initial_result["dir_name"])
        return {"type": "semiconductor", "optics": optics_result}
```

## Monitoring and Debugging

### 1. Prefect UI

Access the web interface at `http://localhost:4200` to:
- Monitor workflow runs in real-time
- View logs and error messages
- Inspect task parameters and results
- Manage deployments and schedules

### 2. Logging

```python
from prefect.logging import get_run_logger

@task
def monitored_task(structure):
    logger = get_run_logger()
    logger.info(f"Processing structure: {structure.formula}")
    
    try:
        result = expensive_calculation(structure)
        logger.info(f"Calculation completed successfully")
        return result
    except Exception as e:
        logger.error(f"Calculation failed: {e}")
        raise
```

### 3. Notifications

```python
@flow
def workflow_with_notifications(structure):
    try:
        result = vasp_band_structure_flow(structure)
        send_notification(f"✅ Workflow completed: {structure.formula}")
        return result
    except Exception as e:
        send_notification(f"❌ Workflow failed: {structure.formula} - {e}")
        raise
```

## Configuration Management

Edit `prefect_config.yaml` to customize:

- **Compute resources**: CPU/memory limits, parallelization
- **VASP settings**: INCAR parameters, k-points, convergence criteria
- **Storage**: Database connections, file paths
- **Monitoring**: Logging levels, alert settings
- **Deployment**: Container images, work pools

## Best Practices

### 1. Task Design

```python
@task(retries=3, retry_delay_seconds=[60, 120, 300])
def robust_vasp_task(structure, **kwargs):
    """Task with exponential backoff retry strategy."""
    # Validate inputs
    if not structure.is_valid:
        raise ValueError("Invalid structure")
    
    # Set up calculation
    # ... 
    
    # Monitor progress
    logger = get_run_logger()
    logger.info(f"Starting calculation for {structure.formula}")
    
    return result
```

### 2. Resource Management

```python
@task(task_run_name="vasp-{structure.formula}")
def resource_aware_task(structure):
    """Task with descriptive naming and resource tagging."""
    # Check available resources
    if psutil.virtual_memory().available < 8e9:  # 8GB
        raise RuntimeError("Insufficient memory")
    
    return result
```

### 3. Error Handling

```python
@flow
def fault_tolerant_workflow(structure):
    """Workflow with graceful error handling."""
    try:
        return main_calculation_path(structure)
    except ConvergenceError:
        logger.warning("Convergence failed, trying alternative settings")
        return fallback_calculation(structure)
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return {"success": False, "error": str(e)}
```

## Troubleshooting

### Common Issues

1. **VASP not found**: Ensure VASP executables are in PATH or set `VASP_COMMAND`
2. **Memory errors**: Adjust task resource limits in deployment configuration
3. **File permissions**: Check that Prefect worker has access to calculation directories
4. **Network issues**: Verify Prefect server connectivity and database access

### Debug Mode

```bash
# Run with detailed logging
PREFECT_LOGGING_LEVEL=DEBUG python prefect_atomate2_example.py

# Check task execution
prefect flow-run logs <flow-run-id>

# Inspect failed tasks
prefect task-run inspect <task-run-id>
```

## Further Resources

- [Prefect Documentation](https://docs.prefect.io/)
- [atomate2 Documentation](https://materialsproject.github.io/atomate2/)
- [jobflow Documentation](https://materialsproject.github.io/jobflow/)
- [Example Workflows Repository](https://github.com/materialsproject/atomate2)

## Contributing

To contribute improvements to this integration:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request with detailed description

For questions or issues, please open an issue on the atomate2 GitHub repository with the "prefect" label.