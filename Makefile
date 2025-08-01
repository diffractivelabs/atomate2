# Makefile for Atomate2 Thermoelectric Calculations with Docker

.PHONY: help build rebuild build-if-needed run-zt run-zt-production run-zt-highthroughput zt-help run-shell test clean

help:
	@echo "Atomate2 Thermoelectric Docker Commands"
	@echo "======================================="
	@echo ""
	@echo "ZT Calculation Commands:"
	@echo "  run-zt                - Run ZT calculation (DEMO mode: fast parameters)"
	@echo "  run-zt-production     - Run ZT calculation (PRODUCTION mode: accurate)"
	@echo "  run-zt-highthroughput - Run high-throughput ZT screening (multiple materials)"
	@echo "  zt-help               - Show detailed ZT calculation example help"
	@echo ""
	@echo "Docker Build Commands:"
	@echo "  build                 - Build Docker image (always builds)"
	@echo "  rebuild               - Force rebuild Docker image (ignore cache)"
	@echo "  build-if-needed       - Build only if image doesn't exist"
	@echo ""
	@echo "Development Commands:"
	@echo "  run-shell             - Open interactive shell in container"
	@echo "  test                  - Test all dependencies are working"
	@echo "  test-workflow         - Test ZT workflow creation"
	@echo "  dev                   - Start development environment"
	@echo "  clean                 - Remove Docker images"
	@echo ""
	@echo "ZT Calculation Modes:"
	@echo "  DEMO mode          : Fast testing (4×4×4 k-pts, 30 Ry, Si structure)"
	@echo "  PRODUCTION mode    : Converged (8×8×8 k-pts, 60 Ry, multiple materials)"
	@echo "  HIGH-THROUGHPUT    : Screen multiple materials with filtering"
	@echo ""
	@echo "Requirements:"
	@echo "  - Docker with buildx support"
	@echo "  - AMD64 platform (for BoltzTraP2 compatibility)"
	@echo ""
	@echo "Quick Start:"
	@echo "  make run-zt           # Run a quick ZT demo (builds if needed)"
	@echo "  make zt-help          # See all ZT calculation options"

# Build the Docker image for AMD64 architecture
build:
	@echo "Building Docker image for AMD64 architecture..."
	@if ! docker buildx ls | grep -q multiarch; then \
		docker buildx create --name multiarch --use; \
	else \
		docker buildx use multiarch; \
	fi
	@docker buildx build --platform linux/amd64 -t atomate2-qe-amd64 . --load
	@echo "✅ Build complete! Image: atomate2-qe-amd64"

# Force rebuild the Docker image (ignores cache)
rebuild:
	@echo "Force rebuilding Docker image (ignoring cache)..."
	@if ! docker buildx ls | grep -q multiarch; then \
		docker buildx create --name multiarch --use; \
	else \
		docker buildx use multiarch; \
	fi
	@docker buildx build --platform linux/amd64 -t atomate2-qe-amd64 . --load --no-cache
	@echo "✅ Rebuild complete! Image: atomate2-qe-amd64"

# Check if image exists and build only if needed
build-if-needed:
	@if ! docker images | grep -q atomate2-qe-amd64; then \
		echo "Image not found, building..."; \
		$(MAKE) build; \
	else \
		echo "✅ Image atomate2-qe-amd64 already exists"; \
	fi

# Run ZT calculation in demo mode (fast parameters)
run-zt: build-if-needed
	@echo "Running ZT Calculation (DEMO mode - fast parameters)..."
	@echo "======================================================="
	@docker run --rm --platform linux/amd64 \
		-v "$(PWD)/examples/zt_calculation.py:/app/examples/zt_calculation.py" \
		--entrypoint /bin/bash atomate2-qe-amd64 \
		-c "source /opt/conda/bin/activate qe-env && cd /app && python3 examples/zt_calculation.py --demo"

# Run ZT calculation in production mode (accurate parameters)
run-zt-production: build-if-needed
	@echo "Running ZT Calculation (PRODUCTION mode - accurate parameters)..."
	@echo "=================================================================="
	@docker run --rm --platform linux/amd64 \
		-v "$(PWD)/examples/zt_calculation.py:/app/examples/zt_calculation.py" \
		--entrypoint /bin/bash atomate2-qe-amd64 \
		-c "source /opt/conda/bin/activate qe-env && cd /app && timeout 1200 python3 examples/zt_calculation.py --production"

# Run high-throughput ZT screening (multiple materials)
run-zt-highthroughput: build-if-needed
	@echo "Running High-Throughput ZT Screening (multiple materials)..."
	@echo "============================================================"
	@docker run --rm --platform linux/amd64 \
		-v "$(PWD)/examples/zt_calculation.py:/app/examples/zt_calculation.py" \
		--entrypoint /bin/bash atomate2-qe-amd64 \
		-c "source /opt/conda/bin/activate qe-env && cd /app && timeout 1800 python3 examples/zt_calculation.py --high-throughput"

# Open interactive shell in the container
run-shell: build-if-needed
	@echo "Opening interactive shell in atomate2 container..."
	@docker run --rm -it --platform linux/amd64 \
		-v "$(PWD):/app" \
		--entrypoint /bin/bash atomate2-qe-amd64 \
		-c "source /opt/conda/bin/activate qe-env && cd /app && exec bash"

# Test that all dependencies are working
test: build-if-needed
	@echo "Testing Dependencies..."
	@echo "======================"
	@docker run --rm --platform linux/amd64 --entrypoint /bin/bash atomate2-qe-amd64 -c "\
		source /opt/conda/bin/activate qe-env && \
		echo '1. Testing Quantum ESPRESSO...' && \
		(pw.x --version 2>/dev/null | head -1 || echo '❌ QE pw.x failed') && \
		echo '2. Testing Python packages...' && \
		python3 -c 'import atomate2; print(\"✅ atomate2:\", \"OK\")' && \
		python3 -c 'import phonopy; print(\"✅ phonopy:\", phonopy.__version__)' && \
		python3 -c 'import ase; print(\"✅ ASE:\", ase.__version__)' && \
		python3 -c 'import BoltzTraP2; print(\"✅ BoltzTraP2: Available\")' && \
		echo '3. Testing workflow creation...' && \
		python3 -c 'from atomate2.espresso.flows.thermoelectric import ZTMaker; print(\"✅ ZT workflow: OK\")' && \
		echo '' && \
		echo '🎉 All dependencies working!'"

# Clean up Docker images
clean:
	@echo "Cleaning up Docker images..."
	@docker rmi atomate2-qe-amd64 2>/dev/null || echo "Image not found"
	@docker system prune -f
	@echo "✅ Cleanup complete"

# Quick test of ZT workflow components
test-workflow: build-if-needed
	@echo "Testing ZT Workflow Components..."
	@echo "================================="
	@docker run --rm --platform linux/amd64 \
		-v "$(PWD)/examples/zt_calculation.py:/app/examples/zt_calculation.py" \
		--entrypoint /bin/bash atomate2-qe-amd64 -c "\
		source /opt/conda/bin/activate qe-env && \
		python3 -c \"\
print('Testing ZT calculation workflow creation...'); \
from atomate2.espresso.flows.thermoelectric import ZTMaker; \
from pymatgen.core import Structure; \
si = Structure([[0,2.73,2.73],[2.73,0,2.73],[2.73,2.73,0]], ['Si','Si'], [[0,0,0],[0.25,0.25,0.25]]); \
zt_maker = ZTMaker(name='test_zt_workflow'); \
flow = zt_maker.make(si); \
print(f'✅ ZT workflow created successfully!'); \
print(f'   - Total jobs: {len(flow.jobs)}'); \
print(f'   - Job names: {[job.name for job in flow.jobs]}'); \
print('✅ Ready for ZT calculations!')\""

# Show ZT calculation example help
zt-help: build-if-needed
	@echo "ZT Calculation Example Help..."
	@echo "=============================="
	@docker run --rm --platform linux/amd64 \
		-v "$(PWD)/examples/zt_calculation.py:/app/examples/zt_calculation.py" \
		--entrypoint /bin/bash atomate2-qe-amd64 \
		-c "source /opt/conda/bin/activate qe-env && cd /app && python3 examples/zt_calculation.py --help"

# Development mode - mount source code
dev: build-if-needed
	@echo "Starting development environment..."
	@docker run --rm -it --platform linux/amd64 \
		-v "$(PWD):/app" \
		-p 8888:8888 \
		--entrypoint /bin/bash atomate2-qe-amd64 \
		-c "source /opt/conda/bin/activate qe-env && cd /app && exec bash"

qe_example: build-if-needed
	@docker run -v "$(PWD):/src" --platform linux/amd64 --rm atomate2-qe-amd64 bash -c "cd /src && export OMPI_MCA_plm_rsh_agent= && export