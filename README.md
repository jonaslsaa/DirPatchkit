# DirPatchkit

A lightweight tool for creating and applying binary patches to directories. This project provides two main functionalities:

- **Patch Creation**: Compare two directories and create a patch (binary or file-based) that captures the differences.
- **Patch Application**: Apply the generated patches to a target directory, with an option to create reverse patches (backups).

## Features

- **Binary Diffing**: Uses [bsdiff4](https://pypi.org/project/bsdiff4/) for generating compact binary patches.
- **New File Handling**: Supports adding new files directly to the patch.
- **GUI and CLI Modes**: A simple GUI built with Tkinter and a command-line interface using [click](https://pypi.org/project/click/).
- **Backup Creation**: Optionally create reverse patches to easily revert changes.

## Installation

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/yourusername/vox-folder-patching-tool.git
    cd vox-folder-patching-tool
    ```

2. **Install Dependencies**:

    Make sure you have Python 3 installed, then run:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Creating a Patch

Use the `patch_create.py` script to generate patches.

- **Binary Mode** (default):

    ```bash
    python patch_create.py /path/to/base /path/to/target --mode binary
    ```

- **File Mode**:

    ```bash
    python patch_create.py /path/to/base /path/to/target --mode file
    ```

Additional options:

- `--patch_dir`: Specify the output patch file or directory.
- `--verbose` or `-v`: Enable verbose output.

### Applying a Patch

Use the `patch_apply.py` script to apply patches.

- **GUI Mode** (default):

    Simply run:

    ```bash
    python patch_apply.py
    ```

    and use the GUI to select your patch file and target folder.

- **CLI Mode**:

    ```bash
    python patch_apply.py --nogui --backup /path/to/target
    ```

    Additional options:

    - `--backup`: Create a reverse patch to revert the applied changes.

## Limitations

* It's quite slow in some cases.
