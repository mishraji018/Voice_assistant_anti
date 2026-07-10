import os
import ast
import json

def get_functions_from_file(filepath):
    functions = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content, filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
    return functions

def main():
    root_dir = r"c:\Users\pmish\Desktop\projects\web development\Voice_Assistant"
    result = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude directories
        dirnames[:] = [d for d in dirnames if d not in ['.git', '__pycache__', 'venv', '.venv', 'build', 'dist', '.tts_cache']]
        
        for file in filenames:
            if file.endswith('.py'):
                filepath = os.path.join(dirpath, file)
                funcs = get_functions_from_file(filepath)
                if funcs:
                    rel_path = os.path.relpath(filepath, root_dir)
                    result[rel_path] = funcs

    with open(os.path.join(root_dir, "brain", "scratch", "function_scan.json"), "w", encoding='utf-8') as f:
        json.dump(result, f, indent=4)
    print("Scan complete")

if __name__ == '__main__':
    # Ensure scratch dir exists
    os.makedirs(r"c:\Users\pmish\Desktop\projects\web development\Voice_Assistant\brain\scratch", exist_ok=True)
    main()
