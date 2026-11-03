#!/usr/bin/env python3
import argparse
import sys
import re
from collections import defaultdict

# Ordered list of regex patterns and their corresponding units.
# The first match found will be used. Add new safe cases here.
UNIT_PATTERNS = [
    (re.compile(r" KG M**-2 S**-1 *$"), "kg m-2 s-1")
    (re.compile(r" KG M-1 S-2 *$"), "kg m-1 s-2")
    (re.compile(r" KG/KG M/S *$"), "m s-1")
    (re.compile(r" M\*\*-2 S\*\*-1 *$"), "m-2 s-1")
    (re.compile(r" KG M-3 *$"), "kg m-3")
    (re.compile(r" KG M-2 *$"), "kg m-2")
    (re.compile(r" KG M/S *$"), "kg m s-1")
    (re.compile(r" M S\*\*-1 *$"), "m s-1")
    (re.compile(r" M S-2 *$"), "m s-2")
    (re.compile(r" W M-2 *$"), "W m-2")
    (re.compile(r" KG/M3 *$"), "kg m-3"), 
    (re.compile(r" KG/KG/S *$"), "s-1")
    (re.compile(r" KG/M2/SEC *$"), "kg m-2 s-1")
    (re.compile(r" KG/M2/S *$"), "kg m-2 s-1")
    (re.compile(r" KG/M2 *$"), "kg m-2"), 
    (re.compile(r" KG/S *$"), "kg s-1"), 
    (re.compile(r" K/S *$"), "K s-1"),
    (re.compile(r" M/S *$"), "m s-1"),
    (re.compile(r" K/S *$"), "K s-1"),
    (re.compile(r" \(PA/S\) *$"), "Pa s-1"),
    (re.compile(r" \(PA/s\) *$"), "Pa s-1"),
    (re.compile(r" W/M\*\*2 *$"), "W m-2"),
    (re.compile(r" W/M2 *$"), "W m-2"),
    (re.compile(r" K *$"), "K"),
    (re.compile(r" \(K\) *$"), "K"),
    (re.compile(r" M *$"), "m"),
    (re.compile(r" m *$"), "m"),
    (re.compile(r" S-1 *$"), "s-1"),
    (re.compile(r" S\*\*-1 *$"), "s-1"),
    (re.compile(r" \(S-1\) *$"), "s-1"),
]

def infer_unit(name):
    """
    Attempt to infer the unit from the end of the STASH name.
    """
    for pattern, unit in UNIT_PATTERNS:
        if pattern.search(name):
            return unit
    return ""

def format_version(v):
    """
    Converts a version string like '10.3' to '1003', or '8.2' to '802'.
    """
    try:
        if '.' in v:
            major, minor = v.split('.')
            return f"{int(major)}{int(minor):02d}"
        return v
    except Exception:
        return v

def check_version_increment(prev_v, new_v):
    """
    Checks if new_v is exactly one minor version greater than prev_v.
    E.g., 10.2 -> 10.3, 10.9 -> 11.0
    """
    try:
        p_major, p_minor = map(int, prev_v.split('.'))
        n_major, n_minor = map(int, new_v.split('.'))
        
        if p_minor == 9:
            expected_major = p_major + 1
            expected_minor = 0
        else:
            expected_major = p_major
            expected_minor = p_minor + 1
            
        if n_major != expected_major or n_minor != expected_minor:
            return False, f"Expected {expected_major}.{expected_minor}, got {new_v}"
        return True, ""
    except ValueError:
        return False, "Versions must be in the format X.Y (e.g., 10.2)"

def sort_key(parts):
    """
    Sorts the entries by Model, STASH code, and then Minimum Version.
    Keeps any non-data lines (like comments) at the top.
    """
    try:
        model = int(parts[0])
        stash = int(parts[1])
    except ValueError:
        return (-1, -1, 0.0)
    
    min_v = parts[4]
    try:
        min_v_float = float(min_v) if min_v else 0.0
    except ValueError:
        min_v_float = 0.0
        
    return (model, stash, min_v_float)

def create_new_entry(model, stash, sm_name, new_v_str, ref_parts=None):
    """
    Helper to create a new CF entry list, inferring units if necessary.
    """
    unit = ""
    std_name = ""
    cond = ""
    coords = ""
    
    if ref_parts:
        unit = ref_parts[3]
        std_name = ref_parts[6]
        cond = ref_parts[7]
        coords = ref_parts[8]
        
    inferred = False
    if not unit.strip():
        unit = infer_unit(sm_name)
        if unit:
            inferred = True
            
    new_parts = [
        str(model),
        str(stash),
        sm_name,
        unit,
        new_v_str,
        "",
        std_name,
        cond,
        coords
    ]
    
    if inferred:
        print(f"Inferred unit: {'!'.join(new_parts)}")
        
    return new_parts

def main():
    parser = argparse.ArgumentParser(description="Update STASH_to_CF.txt with new STASHmaster_A")
    parser.add_argument('--stashmaster', required=True, help="Path to STASHmaster_A")
    parser.add_argument('--stash-to-cf', required=True, help="Path to STASH_to_CF.txt")
    parser.add_argument('--prev-version', required=True, help="Previous UM version (e.g., 10.2)")
    parser.add_argument('--new-version', required=True, help="New UM version (e.g., 10.3)")
    parser.add_argument('--output', required=True, help="Path to output updated STASH_to_CF.txt")
    parser.add_argument('--skip-version-check', action='store_true', help="Disable the check that the new version is exactly one minor version greater than the previous version")

    args = parser.parse_args()

    if not args.skip_version_check:
        is_valid, msg = check_version_increment(args.prev_version, args.new_version)
        if not is_valid:
            print(f"Error: Version increment check failed. {msg}")
            print("Use --skip-version-check to bypass this validation.")
            sys.exit(1)

    prev_v_str = format_version(args.prev_version)
    new_v_str = format_version(args.new_version)

    # Read STASHmaster_A
    stashmaster_entries = {}
    with open(args.stashmaster, 'r') as f:
        for line in f:
            if line.startswith('1|'):
                parts = line.split('|')
                if len(parts) >= 5:
                    try:
                        model = int(parts[1].strip())
                        section = int(parts[2].strip())
                        item = int(parts[3].strip())
                        name = parts[4] # Keep original spacing for the new entry
                        stash_code = section * 1000 + item
                        stashmaster_entries[(model, stash_code)] = name
                    except ValueError:
                        continue

    # Read STASH_to_CF.txt
    cf_entries = []
    with open(args.stash_to_cf, 'r') as f:
        for line in f:
            line = line.strip('\n')
            if not line:
                continue
            parts = line.split('!')
            # Ensure we have exactly 9 columns (0 to 8)
            while len(parts) < 9:
                parts.append("")
            cf_entries.append(parts)

    # Group existing CF entries by (model, stash_code)
    cf_dict = defaultdict(list)
    for i, parts in enumerate(cf_entries):
        try:
            model = int(parts[0])
            stash = int(parts[1])
            cf_dict[(model, stash)].append(i)
        except ValueError:
            continue

    new_entries = []

    for (model, stash), sm_name in stashmaster_entries.items():
        if (model, stash) not in cf_dict:
            # Completely new STASH code
            new_entries.append(create_new_entry(model, stash, sm_name, new_v_str))
        else:
            active_indices = []
            for idx in cf_dict[(model, stash)]:
                if cf_entries[idx][5].strip() == "":
                    active_indices.append(idx)

            if not active_indices:
                # All previous entries were retired. Add a new one.
                last_idx = cf_dict[(model, stash)][-1]
                last_parts = cf_entries[last_idx]
                if last_parts[2].strip() == sm_name.strip():
                    # If the name is the same as the retired one, copy its metadata
                    new_entries.append(create_new_entry(model, stash, sm_name, new_v_str, ref_parts=last_parts))
                else:
                    new_entries.append(create_new_entry(model, stash, sm_name, new_v_str))
                continue

            # Check if the name matches any active entry
            name_matches = False
            for idx in active_indices:
                if cf_entries[idx][2].strip() == sm_name.strip():
                    name_matches = True
                    break

            if not name_matches:
                # Name changed, retire old active entries and create new ones
                for idx in active_indices:
                    cf_entries[idx][5] = prev_v_str
                    ref_parts = cf_entries[idx]
                    new_entries.append(create_new_entry(model, stash, sm_name, new_v_str, ref_parts=ref_parts))

    # Combine and sort
    all_entries = cf_entries + new_entries
    all_entries.sort(key=sort_key)

    # Write output
    with open(args.output, 'w') as f:
        for parts in all_entries:
            f.write('!'.join(parts) + '\n')

if __name__ == '__main__':
    main()
