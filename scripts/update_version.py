from pathlib import Path
import toml

def update_version_in_init():
    pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
    if not pyproject_path.exists():
        print(f'pyproject.toml not found at {pyproject_path}')
        return

    pyproject = toml.load(pyproject_path)
    version = pyproject['tool']['poetry']['version']

    init_file_path = (
        Path(__file__).parent.parent / 'src' / 'patentpack' / '__init__.py'
    )
    if not init_file_path.exists():
        print(f'__init__.py not found at {init_file_path}')
        return

    init_file_content = init_file_path.read_text()
    new_init_file_content = ''
    version_found = False

    for line in init_file_content.split('\n'):
        if line.startswith('__version__'):
            new_init_file_content += f"__version__ = '{version}'\n"
            version_found = True
        else:
            new_init_file_content += f"{line}\n"

    if not version_found:
        new_init_file_content += f"__version__ = '{version}'\n"

    init_file_path.write_text(new_init_file_content.strip())
    print(f'Updated __version__ in __init__.py to {version}')

if __name__ == '__main__':
    update_version_in_init()
