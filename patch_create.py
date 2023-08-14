import os
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

def find_differences(base: str, target: str) -> dict:
    differences = {
        'changed': [],
        'new': []
    }
    
    base_files = set(os.listdir(base))
    target_files = set(os.listdir(target))
    
    # Identify files that are only in the target (new files)
    only_in_target = target_files - base_files
    differences['new'].extend([os.path.join(target, f) for f in only_in_target])
    
    # Check files that are in both directories
    for common_file in base_files.intersection(target_files):
        base_file_path = os.path.join(base, common_file)
        target_file_path = os.path.join(target, common_file)
        
        if os.path.isdir(base_file_path) and os.path.isdir(target_file_path):
            # Recurse into directories
            sub_diff = find_differences(base_file_path, target_file_path)
            differences['changed'].extend(sub_diff['changed'])
            differences['new'].extend(sub_diff['new'])
        elif os.path.isfile(base_file_path) and os.path.isfile(target_file_path):
            if not filecmp.cmp(base_file_path, target_file_path, shallow=False):
                differences['changed'].append(base_file_path)
    
    return differences

def create_binary_patch(base: str, target: str, patch_file: str) -> None:
    differences = find_differences(base, target)
    
    with zipfile.ZipFile(patch_file, 'w') as zipf:
        for diff_file in differences['changed']:
            rel_path = os.path.relpath(diff_file, base)
            target_file_path = os.path.join(target, rel_path)
            
            patch_data = bsdiff4.diff(open(diff_file, 'rb').read(), open(target_file_path, 'rb').read())
            patch_name = f"{rel_path}.patch"
            zipf.writestr(patch_name, patch_data)
            
            if flag_verbose:
                patch_data_size = bytes_to_human_readable(len(patch_data))
                click.echo(f"Created binary patch: {patch_name} ({patch_data_size})")
        
        for new_file in differences['new']:
            rel_path = os.path.relpath(new_file, target)
            zipf.write(new_file, rel_path)
            
            if flag_verbose:
                click.echo(f"Added new file to ZIP: {rel_path}")

def create_file_patch(base: str, target: str, patch_dir: str) -> None:
    differences = find_differences(base, target)

    with zipfile.ZipFile(f"{patch_dir}.zip", 'w') as zipf:
        for i, diff_file in enumerate(differences['changed']):
            rel_path = os.path.relpath(diff_file, base)
            zipf.write(diff_file, rel_path)
            
            if flag_verbose:
                click.echo(f"Added file to ZIP: {rel_path} - {i+1}/{len(differences['changed'])}")

        for i, new_file in enumerate(differences['new']):
            rel_path = os.path.relpath(new_file, target)
            zipf.write(new_file, rel_path)
            
            if flag_verbose:
                click.echo(f"Added new file to ZIP: {rel_path} - {i+1}/{len(differences['new'])}")

@click.command()
@click.argument('base', type=click.Path(exists=True))
@click.argument('target', type=click.Path(exists=True))
@click.option('--patch_dir', type=click.Path(), default=None, help="Directory or file where the patch will be created.")
@click.option('--mode', type=click.Choice(['file', 'binary'], case_sensitive=False), default='file', help="Mode of operation: 'file' or 'binary'.")
@click.option('--verbose', '-v', is_flag=True, default=False, help="Enable verbose output.")
def main(base, target, patch_dir, mode, verbose):
    global flag_verbose
    flag_verbose = verbose
    if verbose:
        click.echo("Verbose output enabled.")
    
    if patch_dir is None:
        script_dir_path = os.path.dirname(os.path.realpath(__file__))
        default_name = f"{os.path.basename(base)}_{os.path.basename(target)}_patch".replace(' ', '_')
        default_path = os.path.join(script_dir_path, default_name)
        click.echo(f"Patch directory not specified, using default: {default_path}")
        patch_dir = f"{default_name}.zip" if mode == 'binary' else default_name
    
    click.echo(f"Comparing {base} and {target} in {mode} mode...")
    if mode == 'binary':
        create_binary_patch(base, target, patch_dir)
    else:
        create_file_patch(base, target, patch_dir)
    click.echo(f"Patch generated at: {patch_dir}")

if __name__ == "__main__":
    main()