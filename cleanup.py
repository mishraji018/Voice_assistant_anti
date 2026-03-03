
import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(ROOT, "backup_legacy")

# Files/Folders to move
TO_ARCHIVE = [
    "core/core.py",
    "commands/data",
    "commands/entertainment",
    "commands/knowledge",
    "commands/productivity",
    "commands/utilities",
    "commands/web",
    "file_list.txt",
    "ARCHITECTURE.md",
    "test" # Move old tests to backup if they are not updated
]

def safe_move(item):
    src = os.path.join(ROOT, item)
    if not os.path.exists(src):
        return
    
    # Create target directory structure in backup
    dst_dir = os.path.join(BACKUP_DIR, os.path.dirname(item))
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    
    dst = os.path.join(BACKUP_DIR, item)
    
    try:
        # If destination already exists, remove it first
        if os.path.exists(dst):
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            else:
                os.remove(dst)
                
        shutil.move(src, dst)
        print(f"[Archived] {item}")
    except Exception as e:
        print(f"[Error] {item}: {e}")

if __name__ == "__main__":
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    print("--- Starting Robust Cleanup ---")
    for item in TO_ARCHIVE:
        safe_move(item)
    print("--- Cleanup Complete ---")
