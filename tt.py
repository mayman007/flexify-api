import os

def rename_files(folder_path):
    # List all files in the specified folder
    files = os.listdir(folder_path)
    
    # Loop through the files and rename each one
    for index, filename in enumerate(files, start=1):
        # Create new filename with the specified format
        new_filename = f"Wallpaper {index}@Author {index}.jpeg"
        
        # Get the full path of the current and new filenames
        old_file_path = os.path.join(folder_path, filename)
        new_file_path = os.path.join(folder_path, new_filename)
        
        # Rename the file
        os.rename(old_file_path, new_file_path)
    
    print("Files renamed successfully!")

# Specify the folder containing the files
folder_path = 'flexify_assets/wallpapers'  # Replace this with the path to your folder
rename_files(folder_path)
