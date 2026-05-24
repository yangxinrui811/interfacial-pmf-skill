# Interfacial PMF Analysis

> Automated free energy calculation for solutes at liquid-liquid/gas interfaces using GROMACS umbrella sampling + WHAM.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://clawhub.ai)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![GROMACS](https://img.shields.io/badge/GROMACS-2020.6%2F2023.3-blue)

---

## Overview

This skill provides a complete, production-tested pipeline for computing Potential of Mean Force (PMF) profiles of solute molecules across liquid interfaces. It was built during a systematic box-size validation study on oil-water interfaces (5 molecular systems × 50 umbrella windows = 250 independent trajectories) and encodes every lesson learned.

**Workflow**:

```mermaid
graph LR
    A[Mol Prep<br/>Gaussian→RESP→.itp] --> B[System Build<br/>Packmol]
    B --> C[EM<br/>+ deep EM fallback]
    C --> D[Pull<br/>Steered MD 5ns]
    D --> E[US Setup<br/>50 windows + md5 verify]
    E --> F[US Run<br/>GPU/HPC parallel]
    F --> G[WHAM<br/>PMF + bootstrap]
    G --> H[Figure<br/>Publication-ready]
```

## Key Features

- **9 Verification Gates** — Automated checks at every step catch errors before they propagate
- **Real Failure Lessons** — Broken files and damage reports from actual production bugs are included as negative examples
- **Dual Platform** — GPU (GROMACS 2023.3, CUDA) and HPC (GROMACS 2020.6, MPI) templates provided
- **All Templates Included** — Ready-to-use `.mdp`, `.itp`, `.top` files from validated simulations

## Quick Start

### Requirements

- **Gaussian 09/16** — molecular structure optimization
- **AmberTools (acpype)** — RESP charge derivation
- **Packmol** — system building
- **GROMACS 2020.6+** — HPC backend (optional)
- **GROMACS 2023.3+** — GPU backend (optional)
- **Python 3.8+** — numpy, matplotlib

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/interfacial-pmf.git
cd interfacial-pmf

# Install Python dependencies
pip install -r requirements.txt

# Verify tools are executable
chmod +x tools/*.sh tools/*.py
```

### Usage

```bash
# Step 1: Prepare solute
python3 tools/mol_prep.py --solute Bpy --smiles "c1ccnc(c1)c2ccncc2" --charge 0

# Step 2: Check topology integrity
bash tools/gate_01_itp.sh Bpy_mol.itp

# Step 3: Build system with Packmol
packmol < system.inp

# Step 4: Run Energy Minimization
gmx_mpi grompp -f templates/em.mdp -c system.gro -p system.top -n index.ndx -o em.tpr -maxwarn 20
gmx_mpi mdrun -deffnm em -v

# Step 5: Run Pull simulation
gmx_mpi grompp -f templates/pull.mdp -c em.gro -p system.top -n index.ndx -o pull.tpr -maxwarn 20
gmx_mpi mdrun -deffnm pull -ntomp 8 -v

# Step 6: Extract US windows
python3 tools/us_setup.py --system Bpy --pull-dir pull --n-windows 50

# Step 7: 🔒 Verify window uniqueness (MANDATORY)
bash tools/gate_05_windows.sh us_windows_k5000_50/

# Step 8: Run US on GPU
bash tools/run_us_gpu.sh 0 49 1
```

## Five Critical Lessons

| # | Lesson | Phase | If Ignored |
|---|--------|-------|------------|
| 1 | `env_setup()` must be **called** (not just defined) | US Setup | 150 identical windows |
| 2 | Never `mpirun` with GROMACS in SGE | Pull | 13× performance drop |
| 3 | Clean checkpoint files before US | US Run | 77% trajectory |
| 4 | Check `.itp` has [bonds] [angles] [dihedrals] | Prep | Molecule rips apart |
| 5 | md5 check after window extraction | US Setup | Undetected duplicates |

## Project Structure

```
interfacial-pmf/
├── CLAWHUB.md           # OpenClaw registry info
├── LICENSE               # MIT License
├── PROJECT_SUMMARY.md    # Detailed project summary
├── README.md             # This file
├── SKILL.md              # OpenClaw skill definition
├── requirements.txt      # Python dependencies
├── .gitignore            # Git ignore rules
├── templates/
│   ├── us.mdp           # Umbrella sampling parameters
│   └── pull.mdp         # Pull simulation parameters
├── tools/
│   ├── mol_prep.py       # Molecular preparation
│   ├── us_setup.py       # Window extraction + md5 verify
│   ├── run_us_gpu.sh     # GPU umbrella sampling
│   ├── gate_01_itp.sh    # 🔒 Gate 1: Topology check
│   └── gate_05_windows.sh # 🔒 Gate 5: md5 dedup check
├── references/           # Reference materials
└── evals/                # Test cases
```

## License

MIT — see [LICENSE](LICENSE).

## Citation

```bibtex
@software{yang2026interfacial,
  title = {Interfacial PMF Analysis: Automated Umbrella Sampling for Liquid Interfaces},
  author = {Yang, Xinrui},
  year = {2026},
  url = {https://github.com/your-org/interfacial-pmf}
}
```

## Acknowledgments

- SobMeme (Beijing Kein) — [Packmol tutorial](http://sobereva.com) and computational chemistry education
- GROMACS development team — MD engine
- OpenClaw AI — Agent skill framework
