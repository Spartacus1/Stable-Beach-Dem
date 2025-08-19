# Stable-Beach-Dem
QGIS plugin that builds an ‘equilibrium’ beach DEM between two polylines. Casts profiles from Line A to Line B, applies a constant slope, then uses a fast profile-constrained raster fill (no IDW/TIN) to synthesize a smooth surface, with optional mask/clip and grid for volumes.
