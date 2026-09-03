import ast
import pathlib
import sys

def get_imports(root_dir):
    imports = set()
    for p in pathlib.Path(root_dir).rglob('*.py'):
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except Exception as e:
            print(f"Error parsing {p}: {e}", file=sys.stderr)
    return imports

if __name__ == "__main__":
    all_imports = get_imports('cyberai')
    # Filter out common stdlib and internal modules if needed, 
    # but it's better to see everything and compare.
    for imp in sorted(all_imports):
        print(imp)