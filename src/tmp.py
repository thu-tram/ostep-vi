import re
from pathlib import Path

def format_chapter_index(chapter_path: Path):
    """
    Reads an index.md file in a given chapter directory, adds image tags
    before figure captions, and saves the formatted content to a new file.

    Args:
        chapter_path: The Path object for the chapter directory.
    """
    # Get the chapter number from the directory name.
    chapter = chapter_path.name
    
    # Define input and output paths
    input_file_path = chapter_path / "index.md"
    output_file_path = chapter_path / "index_formatted.md"

    # Check if the index.md file exists
    if not input_file_path.exists():
        print(f"File not found: {input_file_path}. Skipping...")
        return

    try:
        # Read the content of the index.md file
        with open(input_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Reset figure counter for each chapter
        fig_counter = 1

        def replace_figure(match):
            nonlocal fig_counter
            caption_line = match.group(0)
            # Create the image tag with the correct chapter and figure number
            figure_str = f"![](img/fig{chapter}_{fig_counter}.PNG)\n{caption_line}"
            fig_counter += 1
            return figure_str

        # Regex to find lines starting with **Figure X.Y
        pattern = re.compile(r"^\*\*Figure\s+\d+\.\d+:.*$", re.MULTILINE)
        new_content = pattern.sub(replace_figure, content)

        # Save the new formatted file
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"Successfully processed {input_file_path}. Saved to {output_file_path}.")

    except Exception as e:
        print(f"An error occurred while processing {input_file_path}: {e}")

# Get all directories in the current working directory
current_path = Path(".")
chapter_directories = [d for d in current_path.iterdir() if d.is_dir() and d.name.isdigit()]

# Process each chapter directory
for chapter_dir in sorted(chapter_directories, key=lambda d: int(d.name)):
    format_chapter_index(chapter_dir)

print("\nAll files have been processed.")

