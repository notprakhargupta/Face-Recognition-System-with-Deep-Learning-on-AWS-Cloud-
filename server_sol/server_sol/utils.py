import os

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def is_allowed_file_format(filename, allowed_extensions=ALLOWED_EXTENSIONS):
    """Check if the given filename has an allowed extension."""
    try:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    except Exception as e:
        print(f"Error checking file format for {filename}: {e}")
        return False

def create_directory(directory_path):
    """Create the specified directory if it does not exist."""
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
