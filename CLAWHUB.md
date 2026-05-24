# clawhub: interfacial-pmf

**Interfacial PMF Analysis Skill** — Automated Potential of Mean Force calculation for solutes at liquid-liquid, liquid-gas, or liquid-oil interfaces.

**Tags**: GROMACS, umbrella-sampling, WHAM, PMF, interface, molecular-dynamics, free-energy, packmol

**Authors**: Yang XR (@yangxr-bnu)

## Description

A production-grade OpenClaw skill for computing PMF profiles across liquid interfaces.
The skill encodes 2+ weeks of real-world experience from the `big_box_v2` project
(5 molecular systems × 50 umbrella sampling windows = 250 trajectories).
Every bug encountered is documented as "negative examples" with damage reports.

## Pipeline

1. `mol_prep` — Gaussian → RESP charges → GROMACS .itp
2. `packmol` — Two-phase interface system
3. `em` — Energy minimization (+ deep EM fallback)
4. `pull` — Steered MD along interface normal
5. `us_setup` — Window extraction (+ md5 dedup verification)
6. `us_run` — GPU/HPC umbrella sampling
7. `wham` — PMF reconstruction
8. `plot_pmf` — Publication figure

## 9 Verification Gates

Every step has automated checks that catch errors immediately:
- Gate 1: itp has [bonds] [angles] [dihedrals] (Bpy crash detection)
- Gate 3: Fmax < 200 after EM (prevents Pull crashes)
- Gate 5: md5 dedup on extracted windows (prevents 150-window bug)
- Gate 6: First window sanity test before batch submission

## Key Lessons Encoded

| Lesson | Phase | Damage if missed |
|--------|-------|-----------------|
| `env_setup()` must be called (not just defined) | US Setup | 150 windows all same = 4 days wasted |
| Never use `mpirun` with GROMACS in SGE | Pull/US Run | 13× slower, wrong bug diagnosis |
| md5 dedup check mandatory after extraction | US Setup | Identical start.gro → WHAM garbage |
| Clean checkpoint files before US run | US Run | 77% trajectory (TpBpy w005 bug) |
| `.itp` must have all bond sections | Prep | Molecule ripped apart (Bpy 12 crashes) |

## Dependencies

- Gaussian 09/16
- acpype / AmberTools
- Packmol
- GROMACS 2020.6+ (HPC) / 2023.3+ (GPU)
- Python 3.8+ (numpy)

## Installation

```bash
openclaw skill install interfacial-pmf
```
