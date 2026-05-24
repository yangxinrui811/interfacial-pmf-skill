#!/usr/bin/env bash
# 🔒 GATE 1: itp Integrity Check
# Verify GROMACS topology has all required sections
# Usage: bash gate_01_itp.sh molecule.itp

ITP=$1
if [ -z "$ITP" ]; then echo "Usage: $0 molecule.itp"; exit 1; fi

echo "========================================"
echo "🔒 GATE 1: itp Integrity Check"
echo "  File: $ITP"
echo "========================================"
ERRORS=0

# 1.1 Check required sections — 🚨 Bpy crashed 12x without these!
for sec in atoms bonds angles dihedrals; do
    if grep -q "\[ $sec \]" "$ITP"; then
        echo "  ✅ [$sec] present"
    else
        echo "  ❌ [$sec] MISSING!"
        echo "     → Molecule has no ${sec} potentials!"
        echo "     → Copy from working system or regenerate with proper acpype flags"
        ERRORS=$((ERRORS+1))
    fi
done

# 1.2 Check non-empty sections
for sec in atoms bonds angles dihedrals; do
    count=$(awk "/\[ $sec \]/,/^$/" "$ITP" | grep -c '^\s*[0-9]')
    echo "  [$sec]: $count entries"
    if [ "$sec" = "atoms" ] && [ "$count" -lt 3 ]; then
        echo "  ❌ Too few atoms!"
        ERRORS=$((ERRORS+1))
    fi
    if [ "$sec" = "bonds" ] && [ "$count" -eq 0 ]; then
        echo "  ❌ Zero bonds! Molecule will disintegrate in MD."
        echo "     → Bpy crash 教训: missing bonds → C-C stretches 11×"
        ERRORS=$((ERRORS+1))
    fi
done

# 1.3 Check file size (Bpy broken .itp was only 34 lines)
NLINES=$(wc -l < "$ITP")
echo "  File size: $NLINES lines"
if [ "$NLINES" -lt 50 ]; then
    echo "  ❌ Suspiciously small! < 50 lines — likely missing sections."
    echo "     → Broken Bpy_mol.itp was 34 lines (missing bonds/angles/dihedrals)"
    ERRORS=$((ERRORS+1))
fi

echo "----------------------------------------"
if [ $ERRORS -gt 0 ]; then
    echo "❌ GATE 1 FAILED: $ERRORS errors — fix before proceeding"
    exit 1
else
    echo "✅ GATE 1 PASSED — .itp is complete"
fi
