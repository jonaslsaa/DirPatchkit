import os
import filecmp
import click
import zipfile
import bsdiff4
import xdeltawrapper
import threading
import multiprocessing

flag_verbose = False
flag_large_file_strategy = 'xdelta'
flag_split_size = 16
flag_large_file_size = 32

# Create a lock for flag_split_size access to the zip file
zip_lock = threading.Lock()

def bytes_to_human_readable(num: int) -> str:
    """Convert a number of bytes to a human-readable string."""
    for unit in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return f"{num:.2f} {unit}"
        num /= 1024.0

import concurrent.futures

def is_file_different(file1, file2):
    """Compare two files, first shallowly, then deeply if necessary."""
    if filecmp.cmp(file1, file2, shallow=True):
        return False
    return not filecmp.cmp(file1, file2, shallow=False)

def find_differences(base: str, target: str) -> dict:
    differences = {
        'changed': [],
        'new': []
    }
    if flag_verbose:
        # Print the directories being compared
        click.echo(f"Comparing: {base}")
        click.echo(f"      and: {target}")

    base_entries = {entry.name: entry for entry in os.scandir(base)}
    target_entries = {entry.name: entry for entry in os.scandir(target)}

    # Identify files that are only in the target (new files)
    only_in_target = target_entries.keys() - base_entries.keys()
    differences['new'].extend([os.path.join(target, f) for f in only_in_target])

    # Check files that are in both directories
    common_files = base_entries.keys() & target_entries.keys()
    
    # Use threading for file comparisons
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_file = {executor.submit(is_file_different, base_entries[file].path, target_entries[file].path): file for file in common_files if base_entries[file].is_file() and target_entries[file].is_file()}
        for future in concurrent.futures.as_completed(future_to_file):
            file = future_to_file[future]
            if future.result():
                differences['changed'].append(base_entries[file].path)

    for common_file in common_files:
        base_file_path = base_entries[common_file].path
        target_file_path = target_entries[common_file].path

        if base_entries[common_file].is_dir() and target_entries[common_file].is_dir():
            sub_diff = find_differences(base_file_path, target_file_path)
            differences['changed'].extend(sub_diff['changed'])
            differences['new'].extend(sub_diff['new'])

    return differences


def get_chunk_size():
    return flag_split_size * 1024 * 1024

import multiprocessing

def _diff_process(base_chunk, target_chunk, output_queue):
    # Create the diff in a separate process
    patch_data = bsdiff4.diff(base_chunk, target_chunk)
    # Put the result into the queue
    output_queue.put(patch_data)

def bsdiff4_diff(base_chunk: bytes, target_chunk: bytes) -> bytes:
    """
    Generate bsdiff4 diff in a separate process and return the result.
    """
    
    # Create a queue for inter-process communication
    output_queue = multiprocessing.Queue()
    
    # Create a new process to generate the diff
    process = multiprocessing.Process(target=_diff_process, args=(base_chunk, target_chunk, output_queue))
    process.start()
    process.join()  # Wait for the process to finish
    
    # Get the result from the queue
    patch_data = output_queue.get()
    
    return patch_data

def create_patch_for_file(diff_file: str, target_file_path: str, rel_path: str, zipf: zipfile.ZipFile):
    data_size = os.path.getsize(diff_file)
    if data_size > (flag_large_file_size * 1024 * 1024):
        handle_large_file(diff_file, target_file_path, rel_path, zipf)
    else:
        patch_data = bsdiff4_diff(open(diff_file, 'rb').read(), open(target_file_path, 'rb').read())
        patch_name = f"{rel_path}.patch"
        
        with zip_lock:  # Acquire the lock before writing to the zip file
            zipf.writestr(patch_name, patch_data)

        if flag_verbose:
            patch_data_size = bytes_to_human_readable(len(patch_data))
            original_file_size = bytes_to_human_readable(data_size)
            click.echo(f"Created patch: {patch_name} ({patch_data_size} from {original_file_size})")

def zipf_writestr(zipf, patch_name, patch_data):
    with zip_lock:
        zipf.writestr(patch_name, patch_data)

def zipf_write(zipf, target_file_path, rel_path):
    with zip_lock:
        zipf.write(target_file_path, rel_path)

def split_file_into_chunks(file_path):
    """Split a file into chunks and return the chunks as bytes."""
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(get_chunk_size())
            if not chunk:
                break
            yield chunk

def handle_large_file(diff_file, target_file_path, rel_path, zipf):
    if flag_large_file_strategy == 'copy':
        copy_large_file_to_zip(target_file_path, rel_path, zipf)
    elif flag_large_file_strategy == 'skip':
        skip_large_file(rel_path)
    elif flag_large_file_strategy == 'split' and flag_split_size > 0:
        split_and_patch_large_file(diff_file, target_file_path, rel_path, zipf)
    elif flag_large_file_strategy == 'xdelta':
        xdelta_patch_large_file(diff_file, target_file_path, rel_path, zipf)
    else:
        raise ValueError(f"Unknown large file strategy: {flag_large_file_strategy}")

def copy_large_file_to_zip(target_file_path, rel_path, zipf):
    zipf.write(target_file_path, rel_path)
    if flag_verbose:
        click.echo(f"Added file to ZIP: {rel_path}")

def skip_large_file(rel_path):
    if flag_verbose:
        click.echo(f"Skipping large file: {rel_path}")

def split_and_patch_large_file(diff_file, target_file_path, rel_path, zipf):
    if flag_verbose:
        num_chunks = os.path.getsize(diff_file) // get_chunk_size()
        click.echo(f"File is larger than {flag_large_file_size} MB, splitting into {num_chunks} chunks ({flag_split_size} MB each): {rel_path} ({bytes_to_human_readable(os.path.getsize(diff_file))})")
    # Split the large file into chunks and create a patch for each chunk
    base_chunks = list(split_file_into_chunks(diff_file))
    target_chunks = list(split_file_into_chunks(target_file_path))
    for idx, (base_chunk, target_chunk) in enumerate(zip(base_chunks, target_chunks)):
        patch_data = bsdiff4_diff(base_chunk, target_chunk)
        patch_name = f"{rel_path}.part_{idx}.patch"
        zipf.writestr(patch_name, patch_data)
        
        if flag_verbose:
            click.echo(f"Created patch for chunk {idx}/{len(base_chunks)}: {patch_name} ({bytes_to_human_readable(len(patch_data))} from {bytes_to_human_readable(len(base_chunk))})")

def xdelta_patch_large_file(diff_file, target_file_path, rel_path, zipf):
    if flag_verbose:
        click.echo(f"File is larger than {flag_large_file_size} MB, using xdelta: {rel_path} ({bytes_to_human_readable(os.path.getsize(diff_file))})")
    
    patch_data = xdeltawrapper.create_patch(diff_file, target_file_path)
    patch_name = f"{rel_path}.vcdiff"
    zipf.writestr(patch_name, patch_data)
    
    if flag_verbose:
        patch_data_size = bytes_to_human_readable(len(patch_data))
        click.echo(f"Created patch: {patch_name} ({patch_data_size} from {bytes_to_human_readable(os.path.getsize(diff_file))})")

def create_binary_patch(base: str, target: str, patch_file: str) -> None:
    differences = find_differences(base, target)
    
    if flag_verbose:
        click.echo(f"Found {len(differences['changed'])} changed files and {len(differences['new'])} new files.")
    
    with zipfile.ZipFile(patch_file, 'w') as zipf:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for diff_file in differences['changed']:
                rel_path = os.path.relpath(diff_file, base)
                target_file_path = os.path.join(target, rel_path)
                futures.append(executor.submit(create_patch_for_file, diff_file, target_file_path, rel_path, zipf))
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    click.echo(f"An exception occurred during patch creation: {e}", err=True)
        
        for new_file in differences['new']:
            rel_path = os.path.relpath(new_file, target)
            zipf.write(new_file, rel_path)
            
            if flag_verbose:
                click.echo(f"Added new file to ZIP: {rel_path}")


def create_file_patch(base: str, target: str, patch_dir: str) -> None:
    differences = find_differences(base, target)
    if flag_verbose:
        click.echo(f"\nFound {len(differences['changed'])} changed files and {len(differences['new'])} new files.")

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
@click.option('--large-file-strategy', '--lfs', type=click.Choice(['copy', 'split', 'skip', 'xdelta'], case_sensitive=False), default='xdelta', help="binary: Strategy for large files: 'copy' and 'xdelta' are recommended. ONLY APPLICABLE FOR 'binary' MODE.")
@click.option('--split-size', type=int, default=16, help="binary: Split size in MB for large files. 0 to disable splitting. ONLY APPLICABLE FOR 'split' strategy.")
@click.option('--large-file-size', type=int, default=32, help="binary: Size in MB for large files. Files larger than this will be handled according to the large file strategy.")
def main(base, target, patch_dir, mode, verbose, large_file_strategy, split_size, large_file_size):
    global flag_verbose
    global flag_large_file_strategy
    global flag_split_size
    global flag_large_file_size
    flag_verbose = verbose
    flag_large_file_strategy = large_file_strategy
    flag_split_size = split_size
    flag_large_file_size = large_file_size
    
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