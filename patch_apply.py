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

@click.command()
@click.argument('target', type=click.Path(exists=True))
def main(target):
    """Apply binary patches located in the directory of the TARGET folder."""
    patches = find_patches()
    
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
