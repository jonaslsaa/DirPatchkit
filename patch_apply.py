import os
import click
import zipfile
import bsdiff4

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

def apply_patch(patch_path, target_dir):
    """Apply the binary patch to the target directory."""
    with zipfile.ZipFile(patch_path, 'r') as zipf:
        patch_files = zipf.namelist()
        for patch_file in patch_files:
            if patch_file.endswith('.patch'):
                original_file_path = os.path.join(target_dir, patch_file.replace('.patch', ''))
                
                # Read the original file and the patch data
                with open(original_file_path, 'rb') as orig_file:
                    original_data = orig_file.read()
                patch_data = zipf.read(patch_file)
                
                # Apply the patch
                new_data = bsdiff4.patch(original_data, patch_data)
                
                # Write the patched data back to the original file
                with open(original_file_path, 'wb') as orig_file:
                    orig_file.write(new_data)
            else:
                # For new files, extract them directly
                destination_path = os.path.join(target_dir, patch_file)
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
                with open(destination_path, 'wb') as dest_file:
                    dest_file.write(zipf.read(patch_file))


import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext

def main_gui():
    # Create the main GUI window
    root = tk.Tk()
    root.title("Patch Applier GUI")

    # Variables to hold file paths
    patch_file_path = tk.StringVar()
    target_folder_path = tk.StringVar()
    patches = find_patches()
    patch_file_path.set(patches[0] if patches else "")
    
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
            apply_patch(patch, target)
            log_text.insert(tk.END, f"Applied patch: {patch}\n")
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
@click.argument('target', type=click.Path(exists=True), required=False)
def main(gui, target):
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
        apply_patch(patch, target)
        click.echo(f"Applied patch: {patch}")

if __name__ == "__main__":
    main()
