import re
from pathlib import Path

def fix_file(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    
    # Look for 'from typing import ... Self'
    import_pattern = re.compile(r'from\s+typing\s+import\s+([^,\n]*\bSelf\b[^,\n]*)')
    match = import_pattern.search(text)
    
    if not match:
        return False

    print(f"Fixing {p}")
    
    # Remove 'Self' from the import line
    def replacer(m):
        imports = m.group(1)
        # Split by comma, remove Self, strip, filter empty, rejoin
        parts = [p.strip() for p in imports.split(',') if p.strip() != 'Self']
        if not parts:
            return "from typing import Any" # Fallback
        return f"from typing import {', '.join(parts)}"

    new_text = import_pattern.sub(replacer, text)
    
    # Add compatibility block at the top
    compat_block = (
        "from __future__ import annotations\n"
        "try:\n"
        "    from typing import Self\n"
        "except ImportError:\n"
        "    from typing import Any as Self\n\n"
    )
    new_text = compat_block + new_text
    
    p.write_text(new_text, encoding="utf-8")
    return True

def main():
    fixed_count = 0
    for p in Path("adapters/drakben").rglob("*.py"):
        try:
            if fix_file(p):
                print(f"FIXED {p}")
                fixed_count += 1
        except Exception as e:
            print(f"ERROR {p}: {e}")
    print(f"done: {fixed_count} files fixed")

if __name__ == "__main__":
    main()

import os
import re
from pathlib import Path

def fix_file(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    if "from typing import" not in text or "Self" not in text:
        return False
    
    print(f"Fixing {p}")
    
    # Replace 'from typing import ..., Self, ...' with a block that handles it
    # This is tricky with regex. Let's use a simpler approach: 
    # 1. Remove 'Self' from any 'from typing import' line.
    # 2. Add the compatibility block at the top of the file.
    
    # Remove Self from typing imports
    text = re.sub(r'(from typing import [^,\n]*\bSelf\b[^,\n]*)', r'\1', text) # This is not quite right
    # Let's do it more simply
    lines = text.splitlines()
    new_lines = []
    added_compat = False
    for line in lines:
        if "from typing import" in line and "Self" in line:
            new_line = line.replace("Self,", "").replace(", Self", "").replace("Self", "")
            # Clean up potential double commas or trailing commas
            new_line = re.sub(r',\s*,', ',', new_line)
            new_line = re.sub(r',\s*$', '', new_line)
            new_line = new_line.strip()
            if new_line.endswith(','): # might be multi-line
                 new_line = new_line[:-1]
            new_lines.append(new_line)
            if not added_compat:
                new_lines.insert(0, "from __future__ import annotations")
                new_lines.insert(1, "try:\n    from typing import Self\nexcept ImportError:\n    from typing import Any as Self")
                added_compat = True
        else:
            new_lines.append(line)
            
    p.write_text("\n".join(new_lines), encoding="utf-8")
    return True

def main():
    for p in Path("adapters/drakben").rglob("*.py"):
        try:
            if fix_file(p):
                print(f"FIXED {p}")
        except Exception as e:
            print(f"ERROR {p}: {e}")
    print("done")

if __name__ == "__main__":
    main()
