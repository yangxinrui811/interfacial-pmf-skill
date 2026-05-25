#!/usr/bin/env bash
# GPU Sequential US Runner (grompp + mdrun)
# Usage: bash run_us_gpu.sh <start_win> <end_win> <gpu_id>
#   Example: bash run_us_gpu.sh 0 24 1
#
# Environment variables:
#   SYSTEM  - system name (e.g., "Pa", "TpBpy")
#   BASE    - base directory (override default)
#   US_DIR  - umbrella windows directory (override default)
#
# This script does grompp + mdrun for each window sequentially.
# It is designed to run on GPU servers where GROMACS 2023.3 is
# compiled with CUDA support.
#
# 🚨 Always rm -f pull_prev.cpt pull.cpt before each window
#   (TpBpy w005 bug: residual checkpoint caused partial trajectory)

: ${SYSTEM:="system"}
: ${BASE:="/home/hipeson/Group/yxr/big_box_gpu/${SYSTEM}"}
US_DIR="${BASE}/us_windows_k5000_50"
MDP="${US_DIR}/us.mdp"
TOPO="${US_DIR}/topo"

# GROMACS environment (GPU server)
export LD_LIBRARY_PATH=/opt/software/gcc-9.5.0/lib64:$LD_LIBRARY_PATH
source /opt/software/gmx-2023.3/bin/GMXRC
export PATH=/opt/software/gmx-2023.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/software/gmx-2023.3/lib64:$LD_LIBRARY_PATH

START=${1:-0}
END=${2:-49}
GPU_ID=${3:-1}

echo "GPU US Runner: $SYSTEM windows $START-$END on GPU $GPU_ID"
echo "Start: $(date)"
echo "Base: $BASE"
echo "MDP:  $MDP"
echo "Topo: $TOPO"

for i in $(seq $START $END); do
    WIN=$(printf '%03d' $i)
    WIN_DIR="${US_DIR}/window_${WIN}"

    echo ""
    echo "========================================"
    echo "  Window ${WIN} ($(date))"
    echo "========================================"

    cd "$WIN_DIR" || {
        echo "❌ window_${WIN} not found!"
        exit 1
    }

    # Skip if already complete
    if [ -f "pull.gro" ] && [ -f "pull.edr" ]; then
        echo "  ✅ Already complete, skipping"
        continue
    fi

    # Check start.gro exists
    if [ ! -f "start.gro" ]; then
        echo "❌ start.gro not found in $WIN_DIR!"
        echo "   → Run tool_us_setup first, or copy start.gro from extraction"
        exit 1
    fi

    # 🚨 Clean checkpoint files to prevent continuation (TpBpy w005 bug!)
    rm -f pull_prev.cpt pull.cpt

    # Run grompp (generate TPR from start.gro + topology)
    echo "  grompp..."
    gmx grompp -f "$MDP" -c start.gro -p "${TOPO}/system.top" \
               -n "${TOPO}/index.ndx" -o pull.tpr -maxwarn 20 2>&1

    if [ $? -ne 0 ] || [ ! -f "pull.tpr" ]; then
        echo "❌ grompp FAILED for window ${WIN}!"
        exit 1
    fi

    # Run mdrun on GPU
    echo "  mdrun on GPU ${GPU_ID}..."
    CUDA_VISIBLE_DEVICES=${GPU_ID} gmx mdrun -deffnm pull \
        -nb gpu -v -ntmpi 1 -ntomp 8

    # Verify
    if [ ! -f "pull.gro" ]; then
        echo "❌ Window ${WIN}: pull.gro not generated!"
        echo "   → Check: mdrun may have crashed or been killed"
        echo "   → Check pull.log for error messages"
        exit 1
    fi

    echo "✅ Window ${WIN} done at $(date)"
done

echo ""
echo "🎉 All windows $START to $END complete!"
echo "End: $(date)"
