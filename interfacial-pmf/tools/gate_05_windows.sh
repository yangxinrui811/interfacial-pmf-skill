#!/usr/bin/env bash
# 🔒 GATE 5: Window Uniqueness (🚨 MANDATORY — Never Skip)
# Verify all umbrella windows have unique starting structures
# Usage: bash gate_05_windows.sh /path/to/us_windows_k5000_50

US_DIR=$1
if [ -z "$US_DIR" ]; then
    echo "Usage: $0 /path/to/us_windows_k5000_50"
    exit 1
fi

echo "========================================"
echo "🔒 GATE 5: Window Uniqueness Check"
echo "  Directory: $US_DIR"
echo "========================================"

cd "$US_DIR" || exit 1
ERRORS=0

# 5.1 md5 dedup check — CRITICAL
echo "  Checking md5 uniqueness..."
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
    echo "  Root cause: env_setup() was never called → trjconv failed silently"
    echo "  Fix: 1) Call env_setup() before trjconv"
    echo "       2) Use subprocess.run(check=True) instead of os.system()"
    echo "       3) Remove '2>/dev/null' from trjconv commands"
    echo "       4) Re-run tool_us_setup"
    ERRORS=$((ERRORS+1))
else
    echo "  ✅ All $TOTAL start.gro files are unique"
fi

# 5.2 Verify start.gro timestamps differ
echo ""
echo "  Sampling window times:"
for i in 0 12 24 37 49; do
    f="window_$(printf '%03d' $i)/start.gro"
    if [ -f "$f" ]; then
        header=$(head -1 "$f" 2>/dev/null | grep -oP 't=\s*\K[0-9.]+' || echo "(no time info)")
        echo "    w$(printf '%03d' $i): $header ps"
    fi
done

echo "----------------------------------------"
if [ $ERRORS -gt 0 ]; then
    echo "❌ GATE 5 FAILED — FIX BEFORE PROCEEDING TO US RUN"
    exit 1
else
    echo "✅ GATE 5 PASSED — 50 unique windows ready"
fi
