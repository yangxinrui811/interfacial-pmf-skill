#!/usr/bin/env python3
"""
interfacial-pmf tool: us_setup
===============================
Umbrella window extraction from Pull trajectory.
Extracts N evenly-spaced structures along z, generates tpr.

🔒 CRITICAL: After running, check md5 uniqueness:
  md5sum window_0*/start.gro | awk '{print $1}' | sort | uniq -d
  (must be empty — no duplicates)

Usage:
  python3 us_setup.py --system Pa --pull-dir ../pull --n-windows 50
"""

import os, sys, subprocess, argparse, numpy as np

def env_setup():
    """Set up GROMACS environment — 🚨 MUST be called!"""
    os.environ['LD_LIBRARY_PATH'] = (
        '/export/home/zhucq20/software/openblas-ilp64/lib:'
        '/export/home/zhucq20/software/openmpi-4.1.6/lib:'
        '/export/home/zhucq20/software/plumed-2.8.0/lib'
    )

def main():
    parser = argparse.ArgumentParser(description='Extract US windows from Pull trajectory')
    parser.add_argument('--system', required=True, help='System name')
    parser.add_argument('--pull-dir', required=True, help='Pull directory')
    parser.add_argument('--n-windows', type=int, default=50, help='Number of windows')
    parser.add_argument('--k', type=float, default=5000, help='Spring constant')
    parser.add_argument('--gmx', default='gmx_mpi', help='GROMACS binary')
    parser.add_argument('--dry-run', action='store_true', help='Just print what would be done')
    args = parser.parse_args()

    # 🔒 CRITICAL: Call env_setup() before calling GROMACS
    env_setup()

    BASE = os.path.dirname(os.path.abspath(args.pull_dir))
    US_DIR = os.path.join(BASE, f'us_windows_k5000_{args.n_windows}')
    PULL_DIR = args.pull_dir
    NW = args.n_windows
    GMX = args.gmx
    K = args.k

    os.makedirs(US_DIR, exist_ok=True)

    # Read Pull trajectory
    pullx = os.path.join(PULL_DIR, 'pull_pullx.xvg')
    if not os.path.exists(pullx):
        print(f"❌ Pull data not found: {pullx}")
        sys.exit(1)

    data = np.loadtxt(pullx, comments=['#', '@'])
    times, zvals = data[:, 0], data[:, 1]
    print(f"Load {len(times)} frames from {pullx}")
    print(f"  Time range: {times[0]:.1f} - {times[-1]:.1f} ps")
    print(f"  z range: {zvals[0]:.3f} - {zvals[-1]:.3f} nm")

    # Target positions: -5 to +5 (relative to interface at z=10)
    target_pc = np.linspace(-5.0, 5.0, NW)
    indices = [np.argmin(np.abs(zvals - tc)) for tc in target_pc]

    print(f"\nExtracting {NW} windows...")
    for i in range(NW):
        idx = indices[i]
        t_ps = times[idx]
        pc = target_pc[i]
        z_actual = zvals[idx]

        win_dir = os.path.join(US_DIR, f'window_{i:03d}')
        os.makedirs(win_dir, exist_ok=True)
        gro_file = os.path.join(win_dir, 'start.gro')

        if args.dry_run:
            print(f"  Would extract w{i:03d} at t={t_ps:.1f}ps, z={z_actual:.3f}nm")
            continue

        # Extract frame — use subprocess with check=True
        cmd = f'echo "0" | {GMX} trjconv -f {PULL_DIR}/pull.xtc ' \
              f'-s {PULL_DIR}/pull.tpr -o {gro_file} -dump {t_ps:.1f}'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if not os.path.exists(gro_file) or os.path.getsize(gro_file) < 100:
            print(f"  ❌ w{i:03d}: start.gro extraction FAILED!")
            print(f"  stderr: {result.stderr[:200]}")
            print(f"  → Check: env_setup() called? LD_LIBRARY_PATH correct?")
            sys.exit(1)

        # Generate TPR
        tpr_cmd = f'{GMX} grompp -f {US_DIR}/us.mdp -c {gro_file} ' \
                  f'-p {win_dir}/system.top -n {win_dir}/index.ndx ' \
                  f'-o {win_dir}/pull.tpr -maxwarn 20'
        subprocess.run(tpr_cmd, shell=True, check=True,
                       capture_output=True, text=True)

        if not os.path.exists(f'{win_dir}/pull.tpr'):
            print(f"  ❌ w{i:03d}: TPR generation FAILED!")
            sys.exit(1)

        if i % 10 == 0 or i == NW - 1:
            with open(gro_file) as f:
                title = f.readline().strip()
            print(f"  w{i:03d}: t={t_ps:.1f} pc={pc:.3f} z={z_actual:.3f}  {title}")

    if not args.dry_run:
        print(f"\n=== POST-EXTRACTION VERIFICATION ===")
        # md5 dedup check
        md5s = set()
        for i in range(NW):
            r = subprocess.run(f'md5sum {US_DIR}/window_{i:03d}/start.gro',
                              shell=True, capture_output=True, text=True)
            md5s.add(r.stdout.split()[0])

        if len(md5s) == NW:
            print(f"✅ All {NW} windows have UNIQUE start.gro!")
        else:
            print(f"❌ Only {len(md5s)}/{NW} unique! DUPLICATES DETECTED!")
            print(f"   → env_setup() was NOT called, or GROMACS env missing")
            sys.exit(1)

    print(f"\n[us_setup] Done. {NW} windows ready in {US_DIR}")
    print(f"Next: Run GATE 5 — then tool_us_run")

if __name__ == '__main__':
    main()
