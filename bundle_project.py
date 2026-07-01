import os
from pathlib import Path

# Target extensions to include
INCLUDE_EXTENSIONS = {
    '.py', '.js', '.html', '.css', '.md', '.json', '.yml', '.yaml', '.txt', '.sh', '.bat'
}

# Specific filenames to include even without target extensions
INCLUDE_NAMES = {
    'Dockerfile', 'docker-compose.yml', 'requirements.txt', '.env.example', 'LICENSE'
}

# Directories to exclude
EXCLUDE_DIRS = {
    '.git', '__pycache__', '.venv', 'venv', 'node_modules', 'rf_mapping', '.pytest_cache', 'evidence_store'
}

# Files to exclude specifically (like the output bundle itself)
EXCLUDE_FILES = {
    'raven_cctv_all_code.txt', 'codebase.txt', 'bundle_project.py'
}

def is_text_file(path: Path) -> bool:
    if path.name in INCLUDE_NAMES:
        return True
    if path.suffix.lower() in INCLUDE_EXTENSIONS:
        return True
    return False

def bundle_files(root_dir: Path, output_file: Path):
    count = 0
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("========================================================================\n")
        outfile.write("Raven AI CCTV PROJECT CODEBASE BUNDLE FOR NOTEBOOK LM\n")
        outfile.write(f"Generated at: {Path(output_file).name}\n")
        outfile.write("========================================================================\n\n")
        
        # Walk directories
        for root, dirs, files in os.walk(root_dir):
            # Prune excluded directories in place
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in sorted(files):
                if file in EXCLUDE_FILES:
                    continue
                
                file_path = Path(root) / file
                if not is_text_file(file_path):
                    continue
                
                # Compute relative path
                rel_path = file_path.relative_to(root_dir)
                print(f"Bundling: {rel_path}")
                
                outfile.write("========================================================================\n")
                outfile.write(f"FILE: {rel_path.as_posix()}\n")
                outfile.write("========================================================================\n")
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"\n[ERROR READING FILE: {e}]\n")
                
                outfile.write("\n\n")
                count += 1
                
    print(f"\nDone! Bundled {count} files into {output_file}")

if __name__ == '__main__':
    project_root = Path(__file__).parent
    output_path = project_root / "raven_cctv_all_code.txt"
    bundle_files(project_root, output_path)
