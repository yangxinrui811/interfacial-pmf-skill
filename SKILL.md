# Interfacial PMF Analysis Skill v1.1.0

A production-grade skill for computing Potential of Mean Force (PMF) profiles of solutes at liquid-liquid, liquid-gas, or liquid-oil interfaces, using GROMACS umbrella sampling + WHAM.

**Origin**: 3+ weeks of real-world work on the big_box_v2 project (5 molecular systems × 50 windows = 250 umbrella-sampling trajectories, plus debugging and re-runs). Every lesson is encoded here as positive examples (working templates), negative examples (actual broken files with damage reports), and verification gates (automated checks that prevent bug propagation).

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
| **1** | `tools/gate_01_itp.sh` | itp has [bonds][angles][dihedrals] | Bpy bug: missing bonds → 12 crashes |
| **2** | Manual | System atom count, solute at interface | Wrong box or molecules |
| **3** | Manual | Fmax < 200 after EM | Bpy bug: Fmax=923 → 8 Pull crashes |
| **4** | Manual | Pull z-range coverage | Molecule stuck at interface |
| **5** | `tools/gate_05_windows.sh` | **md5 dedup** on start.gro | Pa bug: 150 identical windows |
| **6** | Manual | First US window sanity test | TpBpy bug: only 77% trajectory |
| **7** | Manual | WHAM histogram overlap | Gaps in reaction coordinate coverage |
| **8** | Visual | PMF physical shape | Unphysical barriers or noise |
| **9** | `tools/gate_05_windows.sh` | **TPR version check** | Bpy bug: mixed 2020.6/2023.3 TPRs → NaN |

## Templates Directory (`templates/`)

| File | Purpose | Key Parameters |
|------|---------|----------------|
| `us.mdp` | Umbrella sampling (k=5000, 3ns, NVT, frozen YY) | 3M steps, dt=0.001, SOLUTE freeze |
| `pull.mdp` | Pull simulation (0.001 nm/ps, 5ns, k=10000) | 5M steps, dt=0.001, NVT |
| `run_us_gpu.sh` | GPU sequential runner (25-50 windows) | GROMACS 2023.3 + CUDA |

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

### 🔴 Lesson 5: TPR Version Must Be Uniform for WHAM
**Bpy — WHAM produced all NaN**. GPU servers ran GROMACS 2023.3, HPC ran GROMACS 2020.6. TPR files from different versions have incompatible binary formats (tpx version 119 vs 129). WHAM silently fails with NaN when fed mixed-version TPRs.

**Fix**: All TPRs used in `gmx wham -it` must come from the **same GROMACS version** running WHAM. When combining data from different servers, re-grompp HPC windows on the GPU server:
```bash
# On the WHAM server, re-grompp all windows from scratch
for i in $(seq 0 49); do
  win=window_$(printf %03d $i)
  cd $win
  gmx grompp -f ../us.mdp -c start.gro -p ../topo/system.top \
             -n ../topo/index.ndx -o pull.tpr -maxwarn 20
done
```

**Verification**: `gmx check -s pull_000.tpr | grep version` should show the same version for all TPRs.

### 🔴 Lesson 6: WHAM -min/-max Must Cover Data Range Exactly
**Bpy — PMF was all NaN even with uniform TPR version**. The WHAM command used `-min -6 -max 6` but the actual pullx data only covers z ≈ -5.0 to +5.0 nm. The outermost bins (±5.5 to ±6.0) had zero sampling → WHAM diverged → NaN.

**Fix**: Check the actual z-range first, then set -min/-max to just cover it:
```bash
# Find actual z-range
awk '!/^[#@]/{if(min==""){min=max=$2}; if($2<min)min=$2; if($2>max)max=$2}
  END{print "z:", min, "to", max}' pullx_000.xvg
# Set -min/-max ~0.5nm inside the range
gmx wham -min <min+0.5> -max <max-0.5> ...
```
For the big_box systems (z range -5.0 to +5.0): use `-min -5.5 -max 5.5`.

### 🔴 Lesson 7: GRO Z-Coordinate Is at Position 37-44 (Not 35-42)
**Phase direction misidentified**. The standard GROMACS GRO format places the z coordinate at columns 37-44:
```
%5d%-5s%5s%5d%8.3f%8.3f%8.3f
|resid||resname||atom||atomnr||--x--||--y--||--z--|
1-5    6-10    11-15  16-20  21-28  29-36  37-44
```
Using `substr($0,35,8)` instead of `substr($0,37,8)` reads from the wrong position and can misidentify the phase layout.

**Fix**: When parsing GRO files with awk, always use `z=substr($0,37,8)`.

### 🔴 Lesson 8: WHAM Bootstrap Takes Very Long
**Pa/TpBpy — bootstrap running for 14+ hours**. The `-nBootstrap 20` flag does 20 complete bootstrap resamples. Each resample runs a full WHAM self-consistent iteration from scratch (potentially 10k-250k iterations per sample). For the 3 systems running simultaneously, this can take 1-2 days on CPU.

**Behavior**: The main WHAM converges first (minutes to hours) and writes the PMF immediately. Bootstrap then runs for each of the 20 resamples. The iter counter in the log resets to ~0 for each new bootstrap sample.

**Workaround**: 
- The base PMF without bootstrap is already available after the main WHAM converges
- Bootstrap only adds error bars. Kill the WHAM early if only the base PMF is needed
- If bootstrap matters: run only `-nBootstrap 10` (instead of 20) for faster results

### ⚠️ Lesson 9: Packmol Produces Loose Structures
**Reference: SobMeme's Packmol tutorial**. Packmol only does geometric packing — no energy relaxation, no electrostatics. The resulting density is always significantly below real density. This is expected.

**Fix**: Always follow Packmol with NPT equilibration (or at minimum long EM + NVT). Never assume the packed density is correct.

### ✅ Lesson 10: GPU US Workflow (Working Pattern)
**Tp, TpPa — 2 × 25 windows on 2 GPU servers**. The validated workflow for running 50 US windows on two GPU servers:

```bash
# On each GPU server (hipeson1: w000-w024, hipeson2: w025-w049):
export LD_LIBRARY_PATH=/opt/software/gcc-9.5.0/lib64:$LD_LIBRARY_PATH
source /opt/software/gmx-2023.3/bin/GMXRC
export LD_LIBRARY_PATH=/opt/software/gmx-2023.3/lib64:$LD_LIBRARY_PATH

CUDA_VISIBLE_DEVICES=1 gmx mdrun -deffnm pull -nb gpu -v -ntmpi 1 -ntomp 8
```
Key points:
- `CUDA_VISIBLE_DEVICES=1` uses the second GPU (GPU 0 often used by LAMMPS)
- `-ntmpi 1 -ntomp 8` for single-GPU with 8 OpenMP threads
- `rm -f pull_prev.cpt pull.cpt` before each new window
- The sequential script (tools/run_us_gpu.sh) does grompp + mdrun per window

### ✅ Lesson 11: GRO Extraction from Pull Trajectory (Binary Search)
**Efficient start.gro extraction**. Instead of running `trjconv -dump` 50 times (each reads the full 681MB trajectory):

```bash
# Step 1: Extract all frames once
echo "System" | gmx trjconv -f pull.xtc -s pull.tpr -o frame_.gro -sep

# Step 2: Binary search for nearest frame to target time
FRAMES=($(ls frame_*.gro | sed 's/frame_//;s/\.gro//' | sort -n))
# For each target time, find closest frame
lo=0; hi=$((${#FRAMES[@]}-1))
while [ $lo -le $hi ]; do
  mid=$(((lo+hi)/2))
  # ... binary search logic
done
cp frame_${best}.gro window_XXX/start.gro
```

### ✅ Lesson 12: Verify GPU Availability Before Submitting
**Check both GPU utilization and memory**:
```bash
nvidia-smi
```
Key indicators:
- GPU 0 vs GPU 1: if GPU 0 has high utilization (LAMMPS), use GPU 1
- Memory usage: GROMACS US uses ~1GB → needs <15GB free
- Two mdrun processes on the same GPU will compete and slow each other down

### ✅ Lesson 13: Phase Layout (Water vs Oil) Must Be Verified
**Critical for PMF interpretation**. The density profile determines which side is water vs oil:

```bash
# Parse GRO file with correct z-column position (37-44)
awk '{resname=substr($0,6,5); gsub(/ /,"",resname);
      z=substr($0,37,8); gsub(/ /,"",z); z+=0;
      if(resname=="SOL") sol++;
      if(resname=="DCM") dcm++}
  END{print "SOL:", sol, "DCM:", dcm}' start.gro
```

For standard bilayer setup (DCM denser than water):
- Bottom (z<10nm): usually **water** (SOL molecules)
- Top (z≥10nm): usually **oil/DCM**
- Interface at z=10nm

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

## Failure Knowledge Base Quick Reference

| Symptom | Root Cause | Fix | Gate |
|---------|-----------|-----|------|
| All start.gro identical | env_setup() not called | Call it; use check=True; remove 2>/dev/null | 5 |
| Pull 13× slower on HPC | mpirun used | Source GMXRC, use gmx_mpi directly | — |
| US only 77% complete | Residual checkpoint | rm -f pull_prev.cpt pull.cpt | 6 |
| Molecule tears apart | Missing bond parameters | Check [bonds]/[angles]/[dihedrals] in .itp | 1 |
| WHAM all NaN | Mixed TPR versions | Re-grompp all windows with same GROMACS | 9 |
| WHAM all NaN (2) | -min/-max range too wide | Match to actual data range | 7 |
| Phase direction wrong | GRO z-column offset | Use substr($0,37,8) not 35-42 | — |
| Bootstrap runs forever | -nBootstrap 20 is slow | Kill early; base PMF already available | 8 |
