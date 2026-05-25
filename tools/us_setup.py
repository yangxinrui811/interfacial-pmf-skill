#!/usr/bin/env python3
"""
interfacial-pmf tool: us_setup v1.1.0
=======================================
Umbrella window extraction from Pull trajectory.
Extracts N evenly-spaced structures along z, generates tpr.

🔒 CRITICAL: After running, check md5 uniqueness:
  md5sum window_0*/start.gro | awk '{print $1}' | sort | uniq -d
  (must be empty — no duplicates)

🔒 CRITICAL: All TPRs must be from the SAME GROMACS version
  gmx check -s window_000/pull.tpr | grep version
  gmx check -s window_049/pull.tpr | grep version
  (both must show the same version)

Usage:
  # Standard: extract 50 windows from Pull trajectory
  python3 us_setup.py --system Pa --pull-dir ../pull --n-windows 50

  # Dry run to preview extraction times
  python3 us_setup.py --system Pa --pull-dir ../pull --n-windows 50 --dry-run

  # On GPU server (GROMACS 2023.3, non-MPI)
  python3 us_setup.py --system Pa --pull-dir ../pull --gmx gmx
"""

import os, sys, subprocess, argparse, numpy as np

def env_setup():
    """
    Set up GROMACS environment — 🚨 MUST BE CALLED!
    This was the root cause of the Pa/TpPa/Tp 150-window bug:
    the function was defined but never called.
    """
    os.environ['LD_LIBRARY_PATH'] = (
        '/export/home/zhucq20/software/openblas-ilp64/lib:'
        '/export/home/zhucq20/software/openmpi-4.1.6/lib:'
        '/export/home/zhucq20/software/plumed-2.8.0/lib'
    )

def check_tpr_versions(us_dir, n_windows, gmx_cmd):
    """Verify all TPR files have the same GROMACS version."""
    versions = set()
    for i in range(n_windows):
        tpr = os.path.join(us_dir, f'window_{i:03d}', 'pull.tpr')
        if not os.path.exists(tpr):
            continue
        r = subprocess.run(f'{gmx_cmd} check -s {tpr} 2>&1',
                          shell=True, capture_output=True, text=True)
        for line in r.stdout.split('\n') + r.stderr.split('\n'):
            if 'version' in line.lower():
                versions.add(line.strip())
    if len(versions) > 1:
        print(f"⚠️  WARNING: Mixed TPR versions detected!")
        for v in versions:
            print(f"   {v}")
        print(f"   → WHAM will fail with all-NaN!")
        print(f"   → Re-grompp all windows with the SAME GROMACS version")
        return False
    elif len(versions) == 1:
        print(f"✅ All TPRs from: {list(versions)[0]}")
        return True
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Extract US windows from Pull trajectory')
    parser.add_argument('--system', required=True, help='System name')
    parser.add_argument('--pull-dir', required=True, help='Pull directory')
    parser.add_argument('--n-windows', type=int, default=50,
                        help='Number of windows (default: 50)')
    parser.add_argument('--k', type=float, default=5000,
                        help='Spring constant (default: 5000)')
    parser.add_argument('--gmx', default='gmx_mpi',
                        help='GROMACS binary (gmx_mpi for HPC, gmx for GPU)')
    parser.add_argument('--z-min', type=float, default=-5.0,
                        help='Min z relative to interface (default: -5.0)')
    parser.add_argument('--z-max', type=float, default=5.0,
                        help='Max z relative to interface (default: 5.0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Just print what would be done')
    args = parser.parse_args()

    # 🔒 CRITICAL: Call env_setup() before calling GROMACS!
    env_setup()

    pull_dir = os.path.abspath(args.pull_dir)
    base = os.path.dirname(pull_dir)
    us_dir = os.path.join(base, f'us_windows_k{int(args.k)}_{args.n_windows}')
    gmx = args.gmx
    nw = args.n_windows

    print(f"=== Umbrella Setup ===")
    print(f"  System:     {args.system}")
    print(f"  Pull dir:   {pull_dir}")
    print(f"  US dir:     {us_dir}")
    print(f"  Windows:    {nw}")
    print(f"  z range:    {args.z_min} to {args.z_max} nm")
    print(f"  GROMACS:    {gmx}")
    print(f"  Spring k:   {args.k}")

    os.makedirs(us_dir, exist_ok=True)

    pullx = os.path.join(pull_dir, 'pull_pullx.xvg')
    if not os.path.exists(pullx):
        print(f"❌ Pull data not found: {pullx}")
        sys.exit(1)

    data = np.loadtxt(pullx, comments=['#', '@'])
    times, zvals = data[:, 0], data[:, 1]
    print(f"\n  Read {len(times)} frames from {pullx}")
    print(f"  Time range: {times[0]:.1f} - {times[-1]:.1f} ps")
    print(f"  z range:    {zvals[0]:.3f} - {zvals[-1]:.3f} nm")

    target_z = np.linspace(args.z_min, args.z_max, nw)
    indices = [np.argmin(np.abs(zvals - tc)) for tc in target_z]

    print(f"\nExtracting {nw} windows...")
    for i in range(nw):
        idx = indices[i]
        t_ps = times[idx]
        z_actual = zvals[idx]
        z_target = target_z[i]

        win_dir = os.path.join(us_dir, f'window_{i:03d}')
        os.makedirs(win_dir, exist_ok=True)
        gro_file = os.path.join(win_dir, 'start.gro')

        if args.dry_run:
            print(f"  w{i:03d}: t={t_ps:8.1f}ps  z_target={z_target:6.2f}  z_actual={z_actual:7.3f}")
            continue

        cmd = (f'echo "0" | {gmx} trjconv -f {pull_dir}/pull.xtc '
               f'-s {pull_dir}/pull.tpr -o {gro_file} -dump {t_ps:.1f}')

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300)

        if not os.path.exists(gro_file) or os.path.getsize(gro_file) < 100:
            print(f"  ❌ w{i:03d}: start.gro extraction FAILED!")
            print(f"  stderr: {result.stderr[:300]}")
            print(f"  → Check: (1) env_setup() called?")
            print(f"  → Check: (2) LD_LIBRARY_PATH correct?")
            sys.exit(1)

        if i % 5 == 0 or i == nw - 1:
            with open(gro_file) as f:
                title = f.readline().strip()
            print(f"  w{i:03d}: t={t_ps:8.1f}ps  z_target={z_target:6.2f}  "
                  f"z_actual={z_actual:7.3f}  {title}")

    if not args.dry_run:
        print(f"\n=== POST-EXTRACTION VERIFICATION ===")
        md5s = set()
        for i in range(nw):
            f = os.path.join(us_dir, f'window_{i:03d}', 'start.gro')
            r = subprocess.run(f'md5sum {f}',
                              shell=True, capture_output=True, text=True)
            md5s.add(r.stdout.split()[0])

        if len(md5s) == nw:
            print(f"✅ md5: All {nw} windows have UNIQUE start.gro!")
        else:
            print(f"❌ md5: Only {len(md5s)}/{nw} unique!")
            sys.exit(1)

        z_actuals = [zvals[idx] for idx in indices]
        print(f"  z range across windows: {min(z_actuals):.3f} to "
              f"{max(z_actuals):.3f} nm")

        z_diffs = np.diff(z_actuals)
        if max(z_diffs) > 0.5:
            print(f"⚠️  Large z-gap detected: {max(z_diffs):.3f} nm")
        else:
            print(f"✅ z-spacing: mean={np.mean(z_diffs):.3f} nm, "
                  f"max={max(z_diffs):.3f} nm")

    print(f"\n[us_setup] Done. {nw} windows ready in {us_dir}")

if __name__ == '__main__':
    main()
