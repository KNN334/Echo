"""Shared surface colors revised to the user's blue-cyan-green-yellow reference."""
from matplotlib.colors import LinearSegmentedColormap

# Visual adaptation of the supplied surface colors, not a recovered publisher LUT.
# Stored separately so the approved base palette and its historical hashes stay intact.
SURFACE_CMAP_NAME = 'reference_blue_cyan_green_yellow'
SURFACE_COLOR_STOPS = [
    (0.00, '#352A87'),
    (0.10, '#1644D8'),
    (0.25, '#087FDD'),
    (0.40, '#00B6CC'),
    (0.55, '#11C69A'),
    (0.70, '#86CE52'),
    (0.82, '#E9DC2D'),
    (1.00, '#F9F80B'),
]
SURFACE_CMAP = LinearSegmentedColormap.from_list(SURFACE_CMAP_NAME, SURFACE_COLOR_STOPS, N=256)
