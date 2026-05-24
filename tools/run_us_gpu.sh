#!/usr/bin/env bash
# GPU Sequential US Runner
# Usage: bash run_us_gpu.sh <start_win> <end_win> <gpu_id>
#   Example: bash run_us_gpu.sh 0 24 1
#
# Environment variables:
#   SYSTEM  - system name (e.g., "Pa", "TpBpy")
#   BASE    - base directory (override default)

: ${SYSTEM:="Pa"}
: ${BASE:="/home/hipeson/Group/yxr/big_box_gpu/${SYSTEM}"}
US_DIR="${BASE}/us_windows_k5000_50"

# GROMACS environment (GPU)
export LD_LIBRARY_PATH=/opt/software/gcc-9.5.0/lib64:$LD_LIBRARY_PATH
source /opt/software/gmx-2023.3/bin/GMXRC
export PATH=/opt/software/gmx-2023.3/bin:$PATH
export LD_LIBRARY_PATH=/opt/software/gmx-2023.3/lib64:$LD_LIBRARY_PATH

START=${1:-0}
END=${2:-49}
GPU_ID=${3:-1}

echo "GPU US Runner: $SYSTEM windows $START-$END on GPU $GPU_ID"
echo "Start: $(date)"

for i in $(seq $START $END); do
    WIN=$(printf '%03d' $i)
    echo ""
    echo "========================================"
    echo "  Window ${WIN} ($(date))"
    echo "========================================"

    cd "${US_DIR}/window_${WIN}" || {
        echo "❌ window_${WIN} not found!"
        exit 1
    }

    # Skip if already complete
    if [ -f "pull.gro" ] && [ -f "pull.edr" ]; then
        echo "  ✅ Already complete, skipping"
        continue
    fi

    # 🚨 Clean checkpoint files to prevent continuation (TpBpy w005 bug!)
    rm -f pull_prev.cpt pull.cpt

    CUDA_VISIBLE_DEVICES=${GPU_ID} gmx mdrun -deffnm pull \
        -nb gpu -v -ntmpi 1 -ntomp 8

    # Verify
    if [ ! -f "pull.gro" ]; then
        echo "❌ Window ${WIN}: pull.gro not generated!"
        exit 1
    fi
    echo "✅ Window ${WIN} done at $(date)"
done

echo ""
echo "🎉 All windows $START to $END complete!"
echo "End: $(date)"
