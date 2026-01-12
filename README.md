# Stable Beach DEM

[![QGIS](https://img.shields.io/badge/QGIS-3.10%2B-93b023?logo=qgis&logoColor=white)](https://qgis.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1-orange.svg)](https://github.com/Spartacus1/Stable-Beach-Dem/releases)

A QGIS plugin for generating **synthetic equilibrium beach surfaces** based on cross-shore profiles and a constant stable slope. Designed for coastal morphology studies, beach nourishment planning, and sediment budget analysis.

---

## Table of Contents

- [Overview](#overview)
- [Scientific Background](#scientific-background)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Parameters Reference](#parameters-reference)
- [Outputs](#outputs)
- [Troubleshooting](#troubleshooting)
- [Why Not IDW/TIN?](#why-not-idwtin)
- [License](#license)
- [Author](#author)

---

## Overview

**Stable Beach DEM** builds a synthetic equilibrium surface between two user-defined polylines representing the beach profile boundaries. The plugin:

1. Generates cross-shore **profiles** from Line A (baseline) toward Line B (limit)
2. Imposes a **constant stable slope** along each profile
3. Synthesizes a continuous **DEM** using profile-constrained raster fill
4. Optionally creates a **mask polygon** and **calculation grid** for volume accounting

This approach is particularly useful for:
- Modeling theoretical equilibrium beach profiles
- Estimating sediment volumes for beach nourishment projects
- Comparing actual topography against equilibrium surfaces
- Coastal erosion/accretion analysis

---

## Scientific Background

### Equilibrium Beach Profile Concept

The plugin implements a simplified equilibrium beach model where the cross-shore profile maintains a constant slope from the baseline to the offshore limit. This represents the theoretical shape a beach would assume under stable wave and sediment conditions.

### Profile Generation

Profiles are cast perpendicular from Line A toward Line B:

```
Line A (baseline)          Line B (limit)
    |                           |
    * -----------------------> *   Profile 1
    * -----------------------> *   Profile 2
    * -----------------------> *   Profile 3
    |                           |
```

Each profile point receives an elevation calculated as:

```
Z(d) = Z0 - d * tan(slope)
```

Where:
- **Z(d)** is the elevation at distance d from the baseline
- **Z0** is the initial elevation (sampled from input DEM at Line A)
- **d** is the horizontal distance along the profile
- **slope** is the user-defined stable slope angle

### Surface Synthesis

Rather than using traditional IDW or TIN interpolation (which can introduce artifacts), the plugin uses a **profile-constrained raster fill** approach that:
- Maintains alignment with profile geometry
- Respects the stable slope assumption
- Fills gaps using GRASS r.fill.stats algorithm

---

## Features

### Tab 1: Stable Beach Generation

- Cross-shore profile generation from Line A to Line B
- Constant slope elevation assignment
- Two sampling modes:
  - **Node-based**: profiles at each vertex of Line A
  - **Distance interval**: profiles at regular spacing along Line A
- Optional surface interpolation with configurable parameters
- Automatic mask polygon creation from profile envelope
- Surface clipping to mask boundary

### Tab 2: Volume Calculation Grid

- Grid generation over mask polygon
- Configurable cell size
- Option to generate only overlapping cells
- Grid attributes include cell ID, centroid coordinates, and area

---

## Requirements

### Software

- **QGIS 3.10 or higher**
- **GRASS GIS 7.x** (for r.fill.stats interpolation)

### Python Dependencies

Standard QGIS Python environment with:
- `numpy`
- `gdal` (osgeo)

---

## Installation

### From ZIP (Recommended)

1. Download the latest release ZIP from [Releases](https://github.com/Spartacus1/Stable-Beach-Dem/releases)
2. Open QGIS and navigate to **Plugins > Manage and Install Plugins**
3. Select **Install from ZIP**
4. Browse to the downloaded file and click **Install Plugin**

### Development Installation

Clone the repository directly into your QGIS plugins folder:

```bash
# Linux
cd ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
git clone https://github.com/Spartacus1/Stable-Beach-Dem.git

# macOS
cd ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/
git clone https://github.com/Spartacus1/Stable-Beach-Dem.git

# Windows (PowerShell)
cd $env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins\
git clone https://github.com/Spartacus1/Stable-Beach-Dem.git
```

Restart QGIS and enable the plugin in **Plugins > Manage and Install Plugins**.

---

## Usage

### Preparing Input Data

1. **DEM Layer**: Load the original terrain model (projected CRS in metres recommended)
2. **Line A**: Digitize the baseline polyline on the beach (profile origins)
3. **Line B**: Digitize the limit polyline (profile targets, typically seaward)

All layers must share the same **projected CRS** with metric units.

### Generating Equilibrium Surface

1. Open **Plugins > Stable Beach DEM**
2. Select the **Stable Beach Generation** tab
3. Configure inputs:
   - Select DEM layer
   - Select Line A (baseline)
   - Select Line B (limit)
   - Enter stable slope (degrees)
4. Choose profile creation mode:
   - **Node Based**: creates profiles at each vertex of Line A
   - **Distance Interval**: creates profiles at regular spacing (enter distance in metres)
5. (Optional) Enable **Generate interpolated surface** and configure parameters
6. Click **Generate**
7. Select output file location (GeoTIFF)

### Generating Volume Grid

1. First generate a DEM with mask (the mask layer must exist)
2. Switch to **Volume Calculation Grid** tab
3. Enter grid cell size (metres)
4. (Optional) Check **Only Generate Overlap Cells** to exclude cells outside mask
5. Click **Generate Grid**

---

## Parameters Reference

### Slope Parameter

| Parameter | Description | Units |
|-----------|-------------|-------|
| **Slope** | Constant beach slope angle | Degrees |

Typical values:
- Dissipative beaches: 1-3 degrees
- Intermediate beaches: 3-6 degrees
- Reflective beaches: 6-12 degrees

### Profile Creation Options

| Option | Description |
|--------|-------------|
| **Node Based** | Creates one profile per vertex in Line A |
| **Distance Interval** | Creates profiles at regular spacing along Line A |

### Interpolation Parameters

When **Generate interpolated surface** is enabled:

| Parameter | Description | Default | Range |
|-----------|-------------|---------|-------|
| **Interpolation mode** | Statistical method for gap filling | wmean | wmean, mean, median, mode |
| **Power** | Distance weighting exponent (for wmean) | 2.0 | > 0 |
| **Number of cells** | Search neighborhood size | 6 | 1-100 |
| **Search distance** | Maximum search radius (relative to cell size) | 0.5 | 0-100 |
| **Do not propagate nulls** | Prevents NoData expansion | Checked | - |

#### Interpolation Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **wmean** | Weighted mean (inverse distance) | General use, smooth surfaces |
| **mean** | Simple arithmetic mean | Uniform data distribution |
| **median** | Median value | Data with outliers |
| **mode** | Most frequent value | Categorical/classified data |

### Grid Parameters

| Parameter | Description |
|-----------|-------------|
| **Grid Cell Size** | Side length of square grid cells (metres) |
| **Only Generate Overlap Cells** | Creates cells only where they intersect the mask |

---

## Outputs

The plugin generates multiple output files in the same directory as the specified output GeoTIFF:

| File | Description |
|------|-------------|
| `<name>.tif` | Raw equilibrium DEM with profile-imposed elevations |
| `<name>_profiles.shp` | Profile polylines connecting Line A to Line B |
| `<name>_input_dem_profile_points.shp` | Profile points with sampled/calculated elevations |
| `<name>_profile_points.shp` | Ordered profile endpoints (Start/End) with vertex index |
| `<name>_mask.shp` | Polygon mask from profile envelope |
| `<name>_surface.tif` | Interpolated continuous surface (if enabled) |
| `<name>_surface_cropped.tif` | Surface clipped to mask boundary |
| `<name>_mask_grid.shp` | Calculation grid over mask (if generated) |

### Profile Points Attributes

| Field | Type | Description |
|-------|------|-------------|
| `ProfNumb` | Integer | Profile number |
| `PointType` | String | "Start" or "End" |
| `Elevation` | Double | Elevation value |
| `X`, `Y` | Double | Point coordinates |
| `vertex_ind` | Integer | Sequential index for polygon creation |

### Grid Attributes

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Cell identifier |
| `centroid_x` | Double | Cell centroid X coordinate |
| `centroid_y` | Double | Cell centroid Y coordinate |
| `area` | Double | Cell area (m2) |

---

## Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Empty or invalid outputs | Line A/B outside DEM extent | Ensure lines overlap DEM and share same CRS |
| Artifacts at edges | Surface extends beyond profiles | Enable interpolation with mask clipping |
| Unexpected elevations | Slope units confusion | Verify slope is in degrees, not percent or ratio |
| Interpolation fails | GRASS not available | Install GRASS GIS and configure in QGIS Processing |
| "No mask layer found" | Grid generated before DEM | Generate DEM first to create mask layer |
| Progress bar stuck | Large area processing | Wait for completion; consider smaller extent |

### Verifying CRS

All input layers must use the same **projected CRS in metres**:

1. Right-click each layer > Properties > Source
2. Verify CRS is projected (not geographic/WGS84)
3. Check units are metres

### GRASS Configuration

If interpolation fails, verify GRASS is properly configured:

1. Go to **Processing > Options > Providers > GRASS**
2. Check that GRASS folder path is set correctly
3. Test with a simple GRASS algorithm

---

## Why Not IDW/TIN?

Empirical testing on beach profiles revealed that standard interpolation methods introduce significant artifacts:

| Method | Issues |
|--------|--------|
| **IDW** | Edge ringing, bulls-eye patterns, extrapolation artifacts |
| **TIN** | Feathering at boundaries, triangulation artifacts with sparse data |

The plugin's **profile-constrained raster fill** approach:
- Maintains strict alignment with profile geometry
- Respects the constant slope assumption throughout
- Uses GRASS r.fill.stats which is optimized for gap-filling rather than full interpolation
- Produces cleaner surfaces with lower computational cost

---

## Roadmap

- Support for variable slope along profiles
- Integration with wave climate data for equilibrium slope estimation
- Multi-temporal analysis tools
- Volume difference calculations between surfaces
- Export to sediment budget reports

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/new-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Authors

**Renato Henriques** and **Ana Emilia Alencar**  
University of Minho, Portugal  
rhenriques@dct.uminho.pt

---

## Citation

If you use this plugin in your research, please cite:

```bibtex
@software{henriques2025stablebeach,
  author = {Henriques, Renato and Figueiredo, Em\'{i}lia},
  title = {Stable Beach DEM: Profile-Based Equilibrium Surface Generator for QGIS},
  year = {2025},
  url = {https://github.com/Spartacus1/Stable-Beach-Dem}
}
```

---

## Acknowledgments

- University of Minho, Department of Earth Sciences; Institute of Earth Sciences
