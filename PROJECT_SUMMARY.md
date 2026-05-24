# Interfacial PMF: Project Summary

## What This Is

A computational chemistry skill for fully automated Potential of Mean Force (PMF) calculation of solute molecules at liquid-liquid or liquid-gas interfaces. The workflow covers the complete pipeline from molecular preparation through umbrella sampling to publication-quality figures.

## Project Background

This project was born from the `big_box_v2` study — a systematic validation of box-size effects on PMF profiles across oil-water interfaces. Five molecular systems (Pa, TpPa, Tp, Bpy, TpBpy — from 24 to ~100 atoms each) were simulated with 50 umbrella sampling windows per system, totaling 250 independent 3ns trajectories.

The workflow was developed iteratively through extensive trial and error. Every failure mode encountered — from missing bond parameters in topology files that caused molecular fragmentation, to silent environment variable bugs that corrupted 150 windows simultaneously — has been documented with root cause analysis and automated detection gates.

## Key Design Decisions

1. **Gate-based verification**: Each processing step has an automated check that must pass before the next step begins. This prevents the common failure pattern of discovering errors only at the final analysis stage.

2. **Negative example documentation**: Real broken files and error patterns are included alongside working templates. This makes failure modes searchable and teachable.

3. **Multi-platform support**: The same pipeline runs on HPC clusters (GROMACS 2020.6, MPI) and GPU workstations (GROMACS 2023.3, CUDA), with platform-specific templates provided.

4. **Lessons as code**: Critical lessons are not just documented but encoded into the tools themselves — e.g., the window extraction script runs an md5 dedup check as a hard requirement before proceeding.

## Reproducibility

All input parameters are provided as templates. The key simulation parameters are:

| Parameter | Pull | US |
|-----------|------|-----|
| Duration | 5 ns | 3 ns/window |
| Spring constant | 10,000 kJ/mol/nm² | 5,000 kJ/mol/nm² |
| Pull rate | 0.001 nm/ps | N/A |
| Windows | N/A | 50 (0.2 nm spacing) |
| Thermostat | V-rescale, 300K | V-rescale, 300K |

## Validation

The skill has been validated against small-box reference calculations for all five systems. Reference PMF values range from 3 kJ/mol (flat interface, small molecule) to 136 kJ/mol (deep well, large molecule crossing oil-water interface).

## Citation

If you use this skill in published work, please cite:

> Yang XR, et al. "Interfacial PMF Analysis: An Automated Umbrella Sampling Workflow for Liquid-Liquid Interfaces." 2026.
