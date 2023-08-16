import os
import subprocess
import tempfile

xdelta_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xdelta.exe')

def random_name():
    import random
    import string
    return ''.join(random.choice(string.ascii_lowercase) for i in range(10)) + '.patch'

def create_patch(old_file, new_file):
    """
    Create a patch from two files using xdelta3.
    
    Parameters:
        old_file (str): The path to the original file.
        new_file (str): The path to the new version of the file.
    
    Returns:
        bytes: The patch data if successful, None otherwise.
    """
    
    try:
        patch_data = subprocess.run([xdelta_exe, '-e', '-s', old_file, new_file], 
                                    stdout=subprocess.PIPE, check=True).stdout
        return patch_data
    except subprocess.CalledProcessError as e:
        print(f"xdelta3 failed with error: {e}")
        return None

def apply_patch(old_file, patch_data, new_file):
    """
    Apply a patch to a file using xdelta3.
    
    Parameters:
        old_file (str): The path to the original file.
        patch_data (bytes): The patch data as bytes.
        new_file (str): The path where the new version of the file will be saved.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    xdelta_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xdelta.exe')
    
    # Create a temporary file to write the patch data
    with tempfile.NamedTemporaryFile(delete=False) as tmp_patch_file:
        tmp_patch_file.write(patch_data)
        tmp_patch_filename = tmp_patch_file.name
    
    try:
        # Use the temporary file as input to xdelta
        subprocess.run([xdelta_exe, '-d', '-f', '-s', old_file, tmp_patch_filename, new_file], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"xdelta3 failed with error: {e}")
        return False
    finally:
        # Clean up the temporary file
        os.remove(tmp_patch_filename)

# Example usage:
if __name__ == '__main__':
    A_txt = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'A.txt')
    B_txt = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'B.txt')
    
    patch_data = create_patch(A_txt, B_txt)
    
    if patch_data is not None:
        print("Patch created successfully.")
    
    restored_file = 'A_patched.txt'
    
    if apply_patch(A_txt, patch_data, restored_file):
        print("Patch applied successfully.")
