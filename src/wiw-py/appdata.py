import pathlib
import os
import shutil

def initialize_app_data(str: data_dir = None):
    '''
    Initializes the app's data directory. If the directory already exists, it will be overwritten. Then copies the default data from the default_data directory to the app_data directory.
    This is usually called by the installer.
    :param data_dir (Optional): The directory containing the default data.
    :type data_dir: str
    '''
    create_app_data_dir()
    if data_dir:
        copy_default_data(data_dir)

def copy_default_data(str: data_dir):
    '''
    Copies the default data from the default_data directory to the app_data directory. If the app_data directory already exists, it will be overwritten.
    IMPORTANT: Copies files only, not directories.
    '''
    app_data_dir = get_app_data_dir()
    if os.path.isdir(data_dir):
        for file in os.listdir(data_dir):
            shutil.copy(data_dir / file, app_data_dir / file)

def get_app_data_dir():
    '''
    Dynamically determines the app's data directory based on the OS. Returns a pathlib.Path object representing the full file path.
    :return: The app's data directory.
    :rtype: pathlib.Path
    ''' 
    if os.name == 'nt': #Windows
        return pathlib.Path(os.getenv("LOCALAPPDATA")) / "myapp"
    elif oos.name == 'posix': #Unix
        return pathlib.Path(os.getenv("XDG_DATA_HOME", "~/.local/share")) / "myapp"
    else:
        raise Exception("Unsupported OS.")
    
def create_app_data_dir():
    '''Creates the app's data directory if it does not already exist.'''
    app_data_dir = get_app_data_dir()
    if not app_data_dir.exists():
        os.makedirs(app_data_dir)

def save_app_data(data):
    '''
    Saves the app's data to the app's data directory.
    '''
    app_data_dir = get_app_data_dir()
    with open(app_data_dir / "data.json", "w") as f:
        f.write(json.dumps(data))

def load_app_data(str: file):
    '''
    Loads a specified file from the app's data directory. Returns the raw data from the file. Returns None if the file does not exist.
    :param str: The name of the file to load.
    :type str: str
    :return: The app's data.
    :rtype: dict (json)
    '''
    app_data_dir = get_app_data_dir()
    if os.path.isfile(app_data_dir / "data.json"):
        with open(app_data_dir / "data.json", "r") as f:
            data = json.load(f)
        return data
    else:
        return None

