"""Fast unit tests for the MMSD sender encoders (no model downloads).

Run from the repository root:  python -m pytest -q tests
"""
import io

import numpy as np
from PIL import Image

import mmsd_sender as ms


def _decode(b):
    return Image.open(io.BytesIO(b))


def test_colourise_maps_classes_to_cityscapes_palette():
    labels = np.array([[0, 13], [11, 18]], dtype=np.uint8)
    rgb = ms.colourise(labels)
    assert rgb.shape == (2, 2, 3)
    assert tuple(rgb[0, 0]) == (128, 64, 128)   # road
    assert tuple(rgb[0, 1]) == (0, 0, 142)      # car
    assert tuple(rgb[1, 0]) == (220, 20, 60)    # person


def test_segmentation_is_webp_at_1024x512():
    labels = np.zeros((1024, 2048), dtype=np.uint8)
    labels[600:, :] = 13
    img = _decode(ms.encode_segmentation(labels))
    assert img.format == "WEBP"
    assert img.size == ms.SEG_SIZE


def test_edges_keep_the_original_resolution():
    rgb = Image.new("RGB", (640, 480), "white")
    img = _decode(ms.encode_edges(ms.canny_edges(rgb)))
    assert img.format == "WEBP"
    assert img.size == (640, 480)


def test_flat_segmentation_map_is_tiny():
    labels = np.zeros((1024, 2048), dtype=np.uint8)
    labels[:512] = 10                            # sky over road
    assert len(ms.encode_segmentation(labels)) < 2_000


def test_summary_shares_add_up_to_one():
    rows = [dict(file="a", file_b=1000, jpeg_b=500, seg_b=10, edge_b=80, caption_b=10, total_b=100),
            dict(file="b", file_b=3000, jpeg_b=1500, seg_b=30, edge_b=240, caption_b=30, total_b=300)]
    s = ms.summarise(rows)
    assert abs(sum(s["share_of_payload"].values()) - 1.0) < 1e-9
    assert s["total_b"]["mean"] == 200
    assert abs(s["payload_vs_file"] - 0.1) < 1e-9


def test_lossless_is_the_default_and_beats_lossy_on_maps():
    labels = np.zeros((1024, 2048), dtype=np.uint8)
    labels[:400] = 10                            # sky
    labels[400:700, 300:900] = 13                # a car
    labels[700:] = 0                             # road
    assert ms.WEBP_LOSSLESS is True
    assert len(ms.encode_segmentation(labels)) < len(ms.encode_segmentation(labels, lossless=False))


def test_parse_size():
    import pytest
    assert ms.parse_size("1024x2048") == (1024, 2048)
    assert ms.parse_size("512X1024") == (512, 1024)
    with pytest.raises(ValueError):
        ms.parse_size("0x10")
