# Interfacial PMF Analysis Skill

A production-grade skill for computing Potential of Mean Force (PMF) profiles of solutes at liquid-liquid, liquid-gas, or liquid-oil interfaces, using GROMACS umbrella sampling + WHAM.

**Origin**: 2+ weeks of real-world work on the big_box_v2 project (5 molecular systems × 50 windows = 250 umbrella-sampling trajectories). Every lesson is encoded here as positive examples (working templates), negative examples (actual broken files with damage reports), and verification gates (automated checks that prevent bug propagation).

**Design**: Tool-set + Planner architecture. 8 standalone tools orchestrated by a Planner agent. 9 verification gates that halt the pipeline if a check fails. A Failure Knowledge Base for diagnosis and repair.

## Tool Set

| Tool | File | Purpose |
|------|------|---------|
| `tool_mol_prep` | `tools/mol_prep.py` | SMILES → Gaussian → RESP charges → GROMACS .itp |
| `tool_packmol` | Use Packmol directly | Build two-phase interface system |
| `tool_em` | GROMACS grompp+mdrun | Energy minimization (deep EM fallback) |
| `tool_pull` | GROMACS grompp+mdrun | Steered MD along interface normal (Z) |
| `tool_us_setup` | `tools/us_setup.py` | Extract N windows from Pull trajectory + verify |
| `tool_us_run` | `tools/run_us_gpu.sh` | Run US windows on GPU/HPC |
| `tool_wham` | GROMACS gmx wham | PMF reconstruction with bootstrap |
| `tool_plot_pmf` | See `nature-figure` skill | Publication-ready PMF plot |

## Verification Gates

| Gate | Script | Check | Fails If |
|------|--------|-------|----------|
| **1** | `tools/gate_01_itp.sh` | itp has [bonds][angles][dihedrals] | Bpy bug: missing bonds → 12 crash |
| **2** | Manual | System atom count, solute at interface | Wrong box or molecules |
| **3** | Manual | Fmax < 200 after EM | Bpy bug: Fmax=923 → 8 Pull crashes |
| **4** | Manual | Pull z-range coverage | Molecule stuck at interface |
| **5** | `tools/gate_05_windows.sh` | **md5 dedup** on start.gro | Pa bug: 150 identical windows |
| **6** | Manual | First US window sanity test | TpBpy bug: only 77% trajectory |
| **7** | Manual | WHAM histogram overlap | Gaps in reaction coordinate coverage |
| **8** | Visual | PMF physical shape | Unphysical barriers or noise |

## Templates Directory (`templates/`)

| File | Purpose |
|------|---------|
| `us.mdp` | Umbrella sampling parameters (k=5000, 3ns) |
| `pull.mdp` | Pull simulation parameters (0.001 nm/ps, 5ns, k=10000) |

## Key Lessons (from real failures)

### 🔴 Lesson 1: env_setup() Must Be Called (Not Just Defined)
**Big_box_v2 — 150 windows corrupted**. The Python function `env_setup()` was defined at the top of `setup_us.py` but **never called**. Result: `gmx_mpi trjconv` ran without `LD_LIBRARY_PATH`, found no OpenBLAS libraries, failed silently (output to `/dev/null`), and every window got the same first-Pull-frame structure.

**Fix**: Call `env_setup()` at module level. Use `subprocess.run(cmd, check=True)` instead of `os.system()`. Remove all `2>/dev/null` from batch commands.

**Detection**: `md5sum window_0*/start.gro | sort | uniq -d` should be empty. If it shows duplicates, this bug has struck again.

### 🔴 Lesson 2: Never Use mpirun with GROMACS
**Big_box_v2 — 13× performance drop**. The Pull submit script used `mpirun gmx_mpi mdrun`. This forced OpenMPI cross-node communication → InfiniBand dependency → TCP fallback → 13× slower. The "IB/TCP shortage" was entirely script-induced.

**Fix**: Source GMXRC and run `gmx_mpi mdrun -deffnm pull -ntomp N -v` directly. SGE passes MPI slots through PMI automatically.

### 🔴 Lesson 3: Checkpoint Files Prevent Fresh US Runs
**TpBpy window_005 — only 77% of intended trajectory**. A residual `pull.cpt` from a previous partial run caused mdrun to continue from checkpoint instead of starting fresh.

**Fix**: Always `rm -f pull_prev.cpt pull.cpt` before a new US window run.

### 🔴 Lesson 4: Missing Bond Parameters → Molecule Ripped Apart
**Bpy — 12 consecutive Pull crashes**. `Bpy_mol.itp` had only 34 lines and zero `[bonds]`, `[angles]`, or `[dihedrals]` sections. C-C bonds stretched 11× normal length at the oil-water interface.

**Fix**: Always run Gate 1 check after .itp generation. Compare .itp file length against a known-good system (e.g., Pa.itp = 71 lines, TpBpy.itp = 208 lines).

### 🔴 Lesson 5: Packmol Produces Loose Structures
**Reference: SobMeme's Packmol tutorial**. Packmol only does geometric packing — no energy relaxation, no electrostatics. The resulting density is always significantly below real density. This is expected.

**Fix**: Always follow Packmol with NPT equilibration (or at minimum long EM + NVT). Never assume the packed density is correct.

## Usage (Autonomous Agent)

```
1. User provides YAML project specification (or answers questions)
2. Planner reads YAML and executes tools in order
3. After each tool, Planner runs the corresponding verification gate
4. If a gate fails:
   a. Log the error
   b. Consult Failure Knowledge Base (this document)
   c. Apply the fix
   d. Re-run the tool
   e. If 3 consecutive failures → stop and report to human
5. If all gates pass → project complete → deliver PMF results
```
