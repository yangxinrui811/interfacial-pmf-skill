#!/usr/bin/env bash
# 🔒 GATE 5+9: Window Uniqueness + TPR Version Check
# 🚨 MANDATORY — Never Skip
# Verify all umbrella windows have unique starting structures
# AND all TPR files come from the same GROMACS version
#
# Usage: bash gate_05_windows.sh /path/to/us_windows_k5000_50 [gmx_binary]

US_DIR=$1
GMX=${2:-gmx}
if [ -z "$US_DIR" ]; then
    echo "Usage: $0 /path/to/us_windows_k5000_50 [gmx_binary]"
    exit 1
fi

echo "========================================"
echo "🔒 GATE 5: Window Uniqueness Check"
echo "🔒 GATE 9: TPR Version Check"
echo "  Directory: $US_DIR"
echo "  GROMACS:   $GMX"
echo "========================================"

cd "$US_DIR" || exit 1
ERRORS=0

echo ""
echo "--- GATE 5: start.gro Uniqueness ---"

MD5S=$(md5sum window_0*/start.gro 2>/dev/null)
if [ -z "$MD5S" ]; then
    echo "  ❌ No start.gro files found!"
    echo "     → Run tool_us_setup first"
    exit 1
fi

UNIQUE=$(echo "$MD5S" | awk '{print $1}' | sort -u | wc -l)
TOTAL=$(echo "$MD5S" | wc -l)
DUPLICATES=$(echo "$MD5S" | awk '{print $1}' | sort | uniq -d)

echo "  Total windows: $TOTAL"
echo "  Unique md5:    $UNIQUE"

if [ "$UNIQUE" -lt "$TOTAL" ]; then
    echo "  ❌ DUPLICATE WINDOWS DETECTED!"
    echo "  Duplicate md5(s): $DUPLICATES"
    echo ""
    echo "  🚨 This is the Pa/TpPa/Tp 150-window bug!"
    echo "  Fix: 1) Call env_setup() before trjconv"
    echo "       2) Use subprocess.run(check=True) instead of os.system()"
    echo "       3) Remove '2>/dev/null' from trjconv commands"
    ERRORS=$((ERRORS+1))
else
    echo "  ✅ All $TOTAL start.gro files are unique"
fi

echo ""
echo "--- GATE 9: TPR Version Consistency ---"

TPR_COUNT=0
TPR_VERSIONS=""
for f in window_0*/pull.tpr; do
    if [ -f "$f" ]; then
        ver=$($GMX check -s "$f" 2>&1 | grep -oP 'VERSION \K[0-9.]+' | head -1)
        if [ -z "$ver" ]; then ver="unknown"; fi
        TPR_VERSIONS="${TPR_VERSIONS}${ver}\n"
        TPR_COUNT=$((TPR_COUNT+1))
    fi
done

UNIQUE_VERSIONS=$(echo -e "$TPR_VERSIONS" | sort -u | grep -v '^$')
NUM_VERSIONS=$(echo "$UNIQUE_VERSIONS" | wc -l)

echo "  TPR files found: $TPR_COUNT"
echo "  Unique versions: $NUM_VERSIONS"

if [ "$NUM_VERSIONS" -gt 1 ]; then
    echo "  ❌ MIXED TPR VERSIONS DETECTED!"
    echo "  🚨 WHAM silently produces NaN!"
    echo "  Fix: Re-grompp all windows on the WHAM server"
    ERRORS=$((ERRORS+1))
elif [ "$NUM_VERSIONS" -eq 1 ]; then
    echo "  ✅ All TPRs from: $(echo -e "$UNIQUE_VERSIONS" | head -1)"
else
    echo "  ⚠️  No TPR files found"
fi

echo ""
echo "----------------------------------------"
if [ $ERRORS -gt 0 ]; then
    echo "❌ GATES FAILED: $ERRORS errors"
    exit 1
else
    echo "✅ ALL GATES PASSED"
fi
