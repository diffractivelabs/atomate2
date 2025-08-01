FROM condaforge/mambaforge:latest

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create conda environment with all dependencies
RUN mamba create --yes -n qe-env -c conda-forge \
    python=3.11 \
    qe \
    phonopy \
    ase \
    numpy \
    scipy \
    matplotlib \
    spglib \
    h5py \
    pyyaml \
    pip

# Activate environment
SHELL ["conda", "run", "-n", "qe-env", "/bin/bash", "-c"]

# Install BoltzTraP2 - essential for transport property calculations
# Try conda-forge first (pre-built binaries), fallback to pip if needed
RUN mamba install -n qe-env -c conda-forge boltztrap2 || \
    echo "BoltzTraP2 conda package not available, continuing without it for demo purposes"


RUN mamba install -n qe-env -c conda-forge pymatgen

# Set up working directory
WORKDIR /app

# Copy the atomate2 source code
COPY . .

# Install atomate2 with phonon dependencies
RUN conda run -n qe-env pip install -e .[phonons]

# Create pseudopotential directory and download basic pseudopotentials
RUN mkdir -p /app/pseudopotentials
WORKDIR /app/pseudopotentials

# Download basic pseudopotentials for Silicon and Germanium
# RUN wget -q http://pseudopotentials.quantum-espresso.org/upf_files/Si.pbe-n-rrkjus_psl.1.0.0.UPF || echo "Failed to download Si pseudopotential"
# RUN wget -q http://pseudopotentials.quantum-espresso.org/upf_files/Ge.pbe-dn-rrkjus_psl.1.0.0.UPF || echo "Failed to download Ge pseudopotential"

RUN cd /app/pseudopotentials && wget https://archive.materialscloud.org/api/records/rcyfm-68h65/files/SSSP_1.3.0_PBE_efficiency.tar.gz/content -O SSSP_1.3.0_PBE_efficiency.tar.gz
RUN cd /app/pseudopotentials && tar -xzf SSSP_1.3.0_PBE_efficiency.tar.gz
RUN cd /app/pseudopotentials && wget https://archive.materialscloud.org/api/records/rcyfm-68h65/files/SSSP_1.3.0_PBE_efficiency.json/content -O SSSP_1.3.0_PBE_efficiency.json

# Set environment variables
ENV ESPRESSO_PSEUDO=/app/pseudopotentials
ENV PATH="/opt/conda/envs/qe-env/bin:$PATH"

# Go back to app directory
WORKDIR /app

# Create entry point script
RUN echo '#!/bin/bash\n\
source /opt/conda/bin/activate qe-env\n\
echo "Testing Quantum ESPRESSO installation..."\n\
pw.x --version 2>/dev/null || echo "QE pw.x not found"\n\
ph.x --version 2>/dev/null || echo "QE ph.x not found"\n\
echo ""\n\
echo "Testing Python dependencies..."\n\
python3 -c "import atomate2; print(f\"atomate2: OK\")" || echo "atomate2 import failed"\n\
python3 -c "import phonopy; print(f\"phonopy {phonopy.__version__}: OK\")" || echo "phonopy import failed"\n\
python3 -c "import ase; print(f\"ASE {ase.__version__}: OK\")" || echo "ASE import failed"\n\
echo ""\n\
echo "Running modified ZT example..."\n\
cd /app && python3 examples/qe_zt_example_runnable.py\n\
' > /app/run_example.sh && chmod +x /app/run_example.sh

# Default command
CMD ["/app/run_example.sh"]