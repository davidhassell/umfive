#!/usr/bin/env python3
import argparse
from collections import defaultdict

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

def main():
    parser = argparse.ArgumentParser(description="Update STASH_to_CF.txt with new STASHmaster_A")
    parser.add_argument('--stashmaster', required=True, help="Path to STASHmaster_A")
    parser.add_argument('--stash-to-cf', required=True, help="Path to STASH_to_CF.txt")
    parser.add_argument('--prev-version', required=True, help="Previous UM version (e.g., 10.2)")
    parser.add_argument('--new-version', required=True, help="New UM version (e.g., 10.3)")
    parser.add_argument('--output', required=True, help="Path to output updated STASH_to_CF.txt")

    args = parser.parse_args()

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
            new_parts = [str(model), str(stash), sm_name, "", new_v_str, "", "", "", ""]
            new_entries.append(new_parts)
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
                    new_parts = [str(model), str(stash), sm_name, last_parts[3], new_v_str, "", last_parts[6], last_parts[7], last_parts[8]]
                else:
                    new_parts = [str(model), str(stash), sm_name, "", new_v_str, "", "", "", ""]
                new_entries.append(new_parts)
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
                    new_parts = [
                        str(model),
                        str(stash),
                        sm_name,
                        ref_parts[3], # units
                        new_v_str,    # min_v
                        "",           # max_v
                        ref_parts[6], # std_name
                        ref_parts[7], # cond
                        ref_parts[8]  # coords
                    ]
                    new_entries.append(new_parts)

    # Combine and sort
    all_entries = cf_entries + new_entries
    all_entries.sort(key=sort_key)

    # Write output
    with open(args.output, 'w') as f:
        for parts in all_entries:
            f.write('!'.join(parts) + '\n')

if __name__ == '__main__':
    main()
