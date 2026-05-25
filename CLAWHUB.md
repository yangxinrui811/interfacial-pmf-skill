# clawhub: interfacial-pmf-skill

**Interfacial PMF Analysis Skill v1.1.0** — Automated Potential of Mean Force calculation for solutes at liquid-liquid, liquid-gas, or liquid-oil interfaces.

**Tags**: GROMACS, umbrella-sampling, WHAM, PMF, interface, molecular-dynamics, free-energy, packmol, bootstrap

**Authors**: Yang XR (@yangxr-bnu)

## Description

A production-grade OpenClaw skill for computing PMF profiles across liquid interfaces.
The skill encodes 3+ weeks of real-world experience from the `big_box_v2` project
(5 molecular systems × 50 umbrella sampling windows = 250+ trajectories).
Every bug encountered is documented as "negative examples" with damage reports.

## Pipeline

1. `mol_prep` — Gaussian → RESP charges → GROMACS .itp
2. `packmol` — Two-phase interface system (→ NPT equilibration)
3. `em` — Energy minimization (+ deep EM fallback: 100k steps SD)
4. `pull` — Steered MD along interface normal
5. `us_setup` — Window extraction (+ md5 dedup + TPR version check)
6. `us_run` — GPU sequential runner (grompp + mdrun per window)
7. `wham` — PMF reconstruction (+ optional bootstrap for error bars)
8. `plot_pmf` — Publication figure

## 9 Verification Gates

| Gate | Check | Prevents |
|------|-------|----------|
| 1 | itp has [bonds][angles][dihedrals] | Bpy 12 crashes (molecule rips apart) |
| 3 | Fmax < 200 after EM | Bpy 8 Pull crashes at interface |
| 5 | md5 dedup on extracted windows | Pa 150-window env_setup() bug |
| 6 | First US window finishes correctly | TpBpy 77% trajectory bug |
| 9 | Uniform TPR version across all windows | Bpy WHAM NaN (mixed 2020.6/2023.3) |

## Key Lessons Encoded (v1.1.0)

| Lesson | Phase | Damage if missed |
|--------|-------|-----------------|
| `env_setup()` must be called (not just defined) | US Setup | 150 windows all same = days wasted |
| Never use `mpirun` with GROMACS in SGE | Pull/US Run | 13× slower, wrong bug diagnosis |
| TPR version uniform for WHAM | WHAM | All-NaN PMF (Bpy + 2020.6/2023.3 mix) |
| WHAM -min/-max must match actual z-range | WHAM | All-NaN from empty edge bins |
| GRO z-column at position 37-44 (not 35-42) | Analysis | Wrong phase assignment |
| Bootstrap (-nBootstrap 20) takes 1-2 days | WHAM | CPU-bound, plan ahead |
| Clean checkpoint files before US run | US Run | 77% trajectory (TpBpy w005) |
| `.itp` must have all bond sections | Prep | Molecule ripped apart |

## Dependencies

- Gaussian 09/16
- acpype / AmberTools
- Packmol
- GROMACS 2020.6+ (HPC) / 2023.3+ (GPU CUDA)
- Python 3.8+ (numpy)

## Installation

```bash
openclaw skill install interfacial-pmf-skill
```
