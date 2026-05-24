#!/usr/bin/env python3
"""
interfacial-pmf tool: mol_prep
===============================
Molecular Preparation: SMILES → Gaussian optimization → RESP charges → GROMACS .itp

Usage:
  python3 mol_prep.py --solute Bpy --smiles "c1ccnc(c1)c2ccncc2" --charge 0

Requires: Gaussian 09/16, AmberTools (antechamber/acpype)
"""

import os, sys, subprocess, argparse, json

def main():
    parser = argparse.ArgumentParser(description='Molecular preparation for interfacial PMF')
    parser.add_argument('--solute', required=True, help='Solute name (3-4 letters)')
    parser.add_argument('--smiles', required=True, help='SMILES string')
    parser.add_argument('--charge', type=int, default=0, help='Net charge')
    parser.add_argument('--method', default='HF/3-21G', help='Optimization method')
    parser.add_argument('--sp-method', default='B3LYP/6-31+G(d)', help='SP method')
    parser.add_argument('--solvent', default='None', help='PCM solvent')
    parser.add_argument('--nproc', type=int, default=16, help='Gaussian CPUs')
    parser.add_argument('--queue', default='renjj20.q', help='SGE queue')
    args = parser.parse_args()

    NAME = args.solute
    CHARGE = args.charge
    NPROC = args.nproc

    print(f"[mol_prep] Preparing {NAME} (charge={CHARGE})...")

    # Step 1: Generate Gaussian optimization input
    gjf_opt = f"""%chk={NAME}_opt.chk
%mem=32GB
%nprocshared={NPROC}
#p {args.method} opt

{NAME} optimization

{CHARGE} 1
  C 0.000 0.000 0.000
"""

    with open(f'{NAME}_opt.gjf', 'w') as f:
        f.write(gjf_opt)
    print(f"  ✅ Created {NAME}_opt.gjf")

    # Step 2: Generate SP input with SCF convergence fix
    if args.solvent != 'None':
        route = f"#p {args.sp_method} SCRF(SMD,Solvent={args.solvent}) geom=check guess=read scf=(maxcycle=512,qc)"
    else:
        route = f"#p {args.sp_method} geom=check guess=read scf=(maxcycle=512,qc)"

    gjf_sp = f"""%chk={NAME}_sp.chk
%mem=32GB
%nprocshared={NPROC}
{route}

{NAME} single point

{CHARGE} 1

"""
    with open(f'{NAME}_sp.gjf', 'w') as f:
        f.write(gjf_sp)
    print(f"  ✅ Created {NAME}_sp.gjf (scf=qc for convergence)")

    # Generate submit script
    submit = f"""#!/bin/bash
#$ -S /bin/bash
#$ -q {args.queue}
#$ -N g09_{NAME}
#$ -pe mpi {NPROC}
#$ -cwd

# 🚨 CRITICAL: Must use renjj20.q for Gaussian jobs!
# zhucq20.q does not have Gaussian environment
export g09root=/export/home/zhucq20/software/g09
export GAUSS_EXEDIR="$g09root/bsd:$g09root/local:$g09root/extras:$g09root"
export PATH="$g09root:$PATH"
export LD_LIBRARY_PATH="$g09root:$LD_LIBRARY_PATH"
export GAUSS_SCRDIR=/tmp/$USER/$JOB_ID
mkdir -p $GAUSS_SCRDIR

# Submit optimization
g09 {NAME}_opt.gjf
if [ $? -ne 0 ]; then
    echo "Gaussian optimization failed!"
    tail -20 {NAME}_opt.log
    exit 1
fi

# Check SCF convergence
if grep -q "Convergence failure" {NAME}_opt.log; then
    echo "SCF convergence failure! Need scf=(maxcycle=512,qc)"
    exit 1
fi

# Submit SP
g09 {NAME}_sp.gjf

# Extract charges
formchk {NAME}_opt.chk {NAME}.fchk
antechamber -i {NAME}_opt.log -fi gout -o {NAME}.mol2 -fo mol2 \\
    -c resp -nc {CHARGE} -at gaff2
acpype -i {NAME}.mol2 -c bcc -d

# Rename for GROMACS
cp {NAME}.acpype/{NAME}_GMX.itp {NAME}.itp

# Verify required sections
echo "=== Verification ==="
for sec in atoms bonds angles dihedrals; do
    if grep -q "\[ $sec \]" {NAME}.itp; then
        echo "  ✅ [$sec] present"
    else
        echo "  ❌ [$sec] MISSING! Run failed."
        exit 1
    fi
done
echo "✅ {NAME}.itp complete"
"""
    with open(f'submit_g09_{NAME}.sh', 'w') as f:
        f.write(submit)
    os.chmod(f'submit_g09_{NAME}.sh', 0o755)

    print(f"\n[mol_prep] Files created:")
    print(f"  {NAME}_opt.gjf     — Optimization input")
    print(f"  {NAME}_sp.gjf      — Single-point input (with scf=qc)")
    print(f"  submit_g09_{NAME}.sh — SGE submit script")
    print(f"\nNext: qsub submit_g09_{NAME}.sh")
    print(f"After completion, run GATE 1: check .itp has [bonds] [angles] [dihedrals]")

if __name__ == '__main__':
    main()
