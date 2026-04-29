import os
import re

def fix_file(path):
    with open(path, 'r') as f:
        content = f.read()
    
    if 'from __future__ import annotations' not in content:
        return

    # Remove all occurrences of the line
    lines = content.splitlines()
    new_lines = [l for l in lines if 'from __future__ import annotations' not in l]
    
    # Insert at the top
    final_content = 'from __future__ import annotations\n' + '\n'.join(new_lines)
    
    # Cleanup extra newlines at top
    final_content = re.sub(r'^(from __future__ import annotations\n)\n+', r'\1\n', final_content)
    
    with open(path, 'w') as f:
        f.write(final_content)

for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
