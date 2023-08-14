import os
import click
import zipfile
import bsdiff4

def bytes_to_human_readable(num: int) -> str:
    """Convert a number of bytes to a human-readable string."""
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

def find_patches():
    """Find all _patch.zip files in this directory."""
    return [f for f in os.listdir() if f.endswith("_patch.zip")]

def validate_patch(patch_path, target_dir):
    """Check if the patch can be applied to the target directory."""
    with zipfile.ZipFile(patch_path, 'r') as zipf:
        patch_files = zipf.namelist()
        for patch_file in patch_files:
            # Only validate files with .patch extension
            if patch_file.endswith('.patch'):
                original_file = os.path.join(target_dir, patch_file.replace('.patch', ''))
                if not os.path.exists(original_file):
                    return False
    return True

def create_reverse_patch(original_data, new_data, reverse_patches, original_file_path):
    """Create a reverse binary patch."""
    reverse_patch_data = bsdiff4.diff(new_data, original_data)
    patch_name = os.path.relpath(original_file_path) + ".patch"
    reverse_patches[patch_name] = reverse_patch_data

def apply_patch_with_backup(patch_path, target_dir, create_backup):
    """Apply the binary patch and optionally create a reverse patch."""
    patch_size = 0
    reverse_patches = {}
    with zipfile.ZipFile(patch_path, 'r') as zipf:
        patch_files = zipf.namelist()
        for patch_file in patch_files:
            if patch_file.endswith('.patch'):
                original_file_path = os.path.join(target_dir, patch_file.replace('.patch', ''))
                
                # Read the original file and the patch data
                with open(original_file_path, 'rb') as orig_file:
                    original_data = orig_file.read()
                patch_data = zipf.read(patch_file)
                patch_size += len(patch_data)
                
                # Apply the patch
                new_data = bsdiff4.patch(original_data, patch_data)
                click.echo(f"Patched: {patch_file}")
                
                if create_backup:
                    create_reverse_patch(original_data, new_data, reverse_patches, original_file_path)
                    click.echo(f"Created reverse patch: {patch_file}")
                
                # Write the patched data back to the original file
                with open(original_file_path, 'wb') as orig_file:
                    orig_file.write(new_data)
            else:
                # For new files, extract them directly
                destination_path = os.path.join(target_dir, patch_file)
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                with open(destination_path, 'wb') as dest_file:
                    dest_file.write(zipf.read(patch_file))

    if create_backup:
        reverse_patch_file = patch_path.replace(".zip", "_revertpatch.zip")
        with zipfile.ZipFile(reverse_patch_file, 'w') as zipf:
            for patch_name, patch_data in reverse_patches.items():
                zipf.writestr(patch_name, patch_data)

    click.echo(f"Patch size: {bytes_to_human_readable(patch_size)}")
    return patch_size


import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext

def main_gui():
    # Create the main GUI window
    root = tk.Tk()
    root.title("Vox's Folder Patching Tool")

    # Variables to hold file paths
    patch_file_path = tk.StringVar()
    target_folder_path = tk.StringVar()
    patches = find_patches()
    patch_file_path.set(patches[0] if patches else "")
    backup_var = tk.BooleanVar()
    
    script_directory = os.path.dirname(os.path.abspath(__file__))
    
    # Define the GUI functions
    def select_patch_file():
        patch_file_path.set(filedialog.askopenfilename(title="Select the Patch File", filetypes=[("ZIP files", "*.zip")], initialdir=script_directory))
        
    def select_target_folder():
        target_folder_path.set(filedialog.askdirectory(title="Select the Target Folder", initialdir=script_directory))

    def apply_patches_gui():
        patches = [patch_file_path.get()]
        target = target_folder_path.get()
        
        if not patches or not target:
            log_text.insert(tk.END, "Patch file or target folder not selected.\n")
            return
        
        log_text.insert(tk.END, f"Found 1 patch. Validating...\n")
        
        if not validate_patch(patches[0], target):
            log_text.insert(tk.END, f"Patch {patches[0]} is not applicable to {target}.\n")
            return
        
        progress_bar['maximum'] = len(patches)
        progress_bar['value'] = 0

        for patch in patches:
            log_text.insert(tk.END, f"Applying patch: {patch} to {target}...\n")
            total_patch_size = apply_patch_with_backup(patch, target, backup_var.get())
            log_text.insert(tk.END, f"Applied patch: {patch} ({bytes_to_human_readable(total_patch_size)})\n")
            if backup_var.get():
                log_text.insert(tk.END, f"Backup patch created for: {patch}\n")
            progress_bar['value'] += 1
        
        log_text.insert(tk.END, "Done.\n")

    # Layout
    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Patch file selection
    ttk.Label(frame, text="Patch File:").grid(row=0, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame, textvariable=patch_file_path, width=40).grid(row=0, column=1, pady=5, padx=5)
    ttk.Button(frame, text="Browse", command=select_patch_file).grid(row=0, column=2, pady=5)

    # Target folder selection
    ttk.Label(frame, text="Target Folder:").grid(row=1, column=0, sticky=tk.W, pady=5)
    ttk.Entry(frame, textvariable=target_folder_path, width=40).grid(row=1, column=1, pady=5, padx=5)
    ttk.Button(frame, text="Browse", command=select_target_folder).grid(row=1, column=2, pady=5)
    
    # Backup checkbox
    ttk.Checkbutton(frame, text="Create backup patch", variable=backup_var).grid(row=5, column=0, columnspan=3, pady=5)

    # Start button
    ttk.Button(frame, text="Start Patching", command=apply_patches_gui).grid(row=2, column=0, columnspan=3, pady=10)

    # Progress bar
    progress_bar = ttk.Progressbar(frame, orient="horizontal", length=200, mode="determinate")
    progress_bar.grid(row=3, column=0, columnspan=3, pady=5)

    # Log text area
    log_text = scrolledtext.ScrolledText(frame, width=50, height=10)
    log_text.grid(row=4, column=0, columnspan=3, pady=10)

    root.mainloop()

@click.command()
@click.option('--gui', is_flag=True, help="Use the GUI instead of the CLI.")
@click.option('--backup', is_flag=True, help="Create a backup patch to reverse changes.")
@click.argument('target', type=click.Path(exists=True), required=False)
def main(gui, backup, target):
    """Apply binary patches located in the directory of the TARGET folder."""
    patches = find_patches()
    
    if gui:
        main_gui()
        return
    if not target:
        click.echo("Target folder not specified.")
        return
    
    if not patches:
        click.echo(f"No patches found in this directory.")
        return
    
    click.echo(f"Found {len(patches)} patches. Validating...")
    for patch in patches:
        if not validate_patch(patch, target):
            click.echo(f"Patch {patch} is not applicable to {target}.")
            return
    
    for patch in patches:
        apply_patch_with_backup(patch, target, backup)
        click.echo(f"Applied patch: {patch}")

if __name__ == "__main__":
    main()
