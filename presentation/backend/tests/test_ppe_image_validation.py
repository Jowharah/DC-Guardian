"""Image validation boundary tests; do not load CUDA or model weights."""
from io import BytesIO
import pytest
from PIL import Image
from presentation.backend.app.ppe_image_validation import validate_image

def image_bytes(format="PNG"):
    output=BytesIO()
    Image.new("RGB",(16,16)).save(output,format=format)
    return output.getvalue()

def test_valid_png():
    image=validate_image(image_bytes())
    assert image.size==(16,16)

def test_valid_jpeg():
    image=validate_image(image_bytes("JPEG"))
    assert image.mode=="RGB"

def test_invalid_bytes_rejected():
    with pytest.raises(ValueError):
        validate_image(b"not an image")

def test_oversized_bytes_rejected():
    with pytest.raises(ValueError):
        validate_image(b"x"*(8*1024*1024+1))
