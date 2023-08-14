
import os
import shutil
import filecmp
import click
import zipfile
import bsdiff4

flag_verbose = False

def bytes_to_human_readable(num: int) -> str:
    """Convert a number of bytes to a human-readable string."""
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

def find_differences(base: str, target: str) -> list:
    differences = []
    
    # Lists of files in the directories
    base_files = set(os.listdir(base))
    target_files = set(os.listdir(target))

    # Check files that are in both directories
    for common_file in base_files.intersection(target_files):
        base_file_path = os.path.join(base, common_file)
        target_file_path = os.path.join(target, common_file)
        
        if os.path.isdir(base_file_path) and os.path.isdir(target_file_path):
            # If it's a directory, recurse into it
            differences.extend(find_differences(base_file_path, target_file_path))
        elif os.path.isfile(base_file_path) and os.path.isfile(target_file_path):
            # If it's a file, compare contents
            if not filecmp.cmp(base_file_path, target_file_path, shallow=False):
                differences.append(base_file_path)
    
    return differences

def create_binary_patch(base: str, target: str, patch_file: str) -> None:
    differences = find_differences(base, target)
    
    with zipfile.ZipFile(patch_file, 'w') as zipf:
        for diff_file in differences:
            rel_path = os.path.relpath(diff_file, base)
            target_file_path = os.path.join(target, rel_path)
            
            # Generate binary patch
            patch_data = bsdiff4.diff(open(diff_file, 'rb').read(), open(target_file_path, 'rb').read())
            patch_name = f"{rel_path}.patch"
            
            # Add the binary patch to the ZIP file
            zipf.writestr(patch_name, patch_data)
            
            # Log if verbose
            if flag_verbose:
                patch_data_size = bytes_to_human_readable(len(patch_data))
                click.echo(f"Created binary patch: {patch_name} ({patch_data_size})")

def create_file_patch(base: str, target: str, patch_dir: str) -> None:
    differences = find_differences(base, target)

    with zipfile.ZipFile(f"{patch_dir}.zip", 'w') as zipf:
        for diff_file in differences:
            rel_path = os.path.relpath(diff_file, base)
            zipf.write(diff_file, rel_path)
            
            if flag_verbose:
                click.echo(f"Added file to ZIP: {rel_path}")


@click.command()
@click.argument('base', type=click.Path(exists=True))
@click.argument('target', type=click.Path(exists=True))
@click.option('--patch_dir', type=click.Path(), default=None, help="Directory or file where the patch will be created.")
@click.option('--mode', type=click.Choice(['file', 'binary'], case_sensitive=False), default='file', help="Mode of operation: 'file' or 'binary'.")
@click.option('--verbose', '-v', is_flag=True, default=True, help="Enable verbose output.")
def main(base, target, patch_dir, mode, verbose):
    """Generate a patch based on differences between BASE and TARGET."""
    global flag_verbose
    flag_verbose = verbose
    
    # Default patch directory or file
    if patch_dir is None:
        default_name = f"{os.path.normpath(target)}_patch"
        patch_dir = f"{default_name}.zip" if mode == 'binary' else default_name
    
    click.echo(f"Comparing {base} and {target} in {mode} mode...")
    if mode == 'binary':
        create_binary_patch(base, target, patch_dir)
    else:
        create_file_patch(base, target, patch_dir, zip)
    output_type = "ZIP file" if (zip and mode == 'file') or mode == 'binary' else "directory"
    click.echo(f"Patch {output_type} generated at: {patch_dir}")

if __name__ == "__main__":
    main()
