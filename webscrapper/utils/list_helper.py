from typing import Dict, List, Optional


def remove_duplicates_from_list(
    data: List[Dict],
    columns: List[str],
    keys_to_remove: Optional[List[str]] = None,
    strip: bool = True,
    preserve_order: bool = True
) -> tuple[List[Dict], List[Dict]]:
    # Copy to avoid mutating the original list?
    # We'll work on the given list, but if keys_to_remove is provided, we modify entries.
    # If the caller wants to preserve original data, they should pass a copy.

    if keys_to_remove:
        for entry in data:
            for key in keys_to_remove:
                if key in entry:
                    del entry[key]

    seen = set()
    unique = []
    duplicates = []
    
    print('type(data): ', type(data))


    for entry in data:
        
        if type(entry) == dict:
            src = entry.get(columns[0], "")
            tgt = entry.get(columns[1], "")
        else:
            src = entry[0]
            tgt = entry[1]
        if strip:
            src = src.strip()
            tgt = tgt.strip()
        pair = (src, tgt)

        if pair in seen:
            duplicates.append(entry)
        else:
            seen.add(pair)
            unique.append(entry)

    if not preserve_order:
        # If order doesn't matter, we could just return unique (order from iteration)
        pass

    return unique, duplicates
