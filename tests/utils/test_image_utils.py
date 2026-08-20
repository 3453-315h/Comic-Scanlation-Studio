import pytest
from pathlib import Path
from src.utils.image_utils import load_image

def test_load_image_raises_value_error(tmp_path: Path):
    """Test that load_image raises ValueError when given a non-image file."""
    # Create a dummy text file
    dummy_file = tmp_path / "not_an_image.txt"
    dummy_file.write_text("This is not an image file.")

    # Assert that loading the non-image file raises a ValueError
    with pytest.raises(ValueError, match="Failed to load image"):
        load_image(dummy_file)
