#!/usr/bin/env python3
import os
import sys
import subprocess

# Find run.py in the container
for root, dirs, files in os.walk('/app'):
    if 'run.py' in files:
        print(f"Found run.py at: {root}")
        os.chdir(root)
        # Execute run.py with the correct arguments
        subprocess.run([sys.executable, 'run.py', '--port', '8080', '--no-browser'])
        sys.exit(0)

print("Could not find run.py!")
print("Directory contents:")
for root, dirs, files in os.walk('/app'):
    level = root.replace('/app', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f"{indent}{os.path.basename(root)}/")
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        print(f"{subindent}{file}")
sys.exit(1)