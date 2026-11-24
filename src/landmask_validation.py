from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from shapely.geometry import box

RGB = 3  # number of color channels


def _normalize(arr: np.ndarray) -> np.ndarray:
    """Normalize an array to [0, 1]."""
    if arr.max() > arr.min():
        return (arr - arr.min()) / (arr.max() - arr.min())
    return arr


def _false_color(data: np.ndarray) -> np.ndarray:
    """Create a compound false color composite using all bands: band i is averaged into channel i % 3."""
    n_bands, height, width = data.shape
    if n_bands == RGB:
        return np.dstack([_normalize(band) for band in data])
    channels = np.zeros((RGB, height, width), dtype=np.float32)
    counts = np.zeros(RGB)
    for i, band in enumerate(data):
        channels[i % RGB] += _normalize(band)
        counts[i % RGB] += 1
    for c in range(RGB):
        if counts[c] > 0:
            channels[c] /= counts[c]
    return np.moveaxis(channels, 0, -1)


def inspect_fp(fp1: Path) -> None:
    """
    Inspect a raster file and display its metadata and a false color composite.
    Parameters:
        fp1: Path to the raster file.
    """
    with rasterio.open(fp1) as src:
        print("Number of bands:", src.count)
        print("CRS:", src.crs)
        print("Bounds:", src.bounds)
        print("Transform:", src.transform)
        data = src.read()  # Reads all bands; shape: (bands, height, width)
        print("Data shape:", data.shape)

    # Build a list of images and corresponding titles for plotting
    images = []
    titles = []

    # Only add the false color composite if more than one band exists
    if len(data) > 1:
        images.append(_false_color(data))
        titles.append("Composite False Color")

    # Add the true color composite if at least three bands exist
    if len(data) >= RGB:
        images.append(np.dstack([_normalize(band) for band in data[:RGB]]))
        titles.append("True Color")

    # Add each individual band in grayscale
    for i, band in enumerate(data):
        images.append(_normalize(band))
        titles.append(f"Band {i + 1}")

    total_images = len(images)
    _, axs = plt.subplots(1, total_images, figsize=(5 * total_images, 5), squeeze=False)

    for ax, img, title in zip(axs[0], images, titles, strict=True):
        # If image has three channels, display as is; otherwise use a grayscale colormap.
        if img.ndim == RGB and img.shape[2] == RGB:
            ax.imshow(img)
        else:
            ax.imshow(img, cmap="gray")
        ax.set_title(title)
        ax.axis("off")

    plt.tight_layout()
    plt.show()


def plot_shp_and_raster_bounds(fp_shp: Path, fp_tif: Path) -> None:
    """
    Plots a shapefile with a red rectangle representing the bounds of a GeoTIFF raster.

    Parameters:
        fp_shp: Path to the shapefile.
        fp_tif: Path to the raster (GeoTIFF) file.
    """
    # Read the shapefile
    gdf = gpd.read_file(fp_shp)

    # Open the raster file and extract its bounds and CRS
    with rasterio.open(fp_tif) as src:
        bounds = src.bounds
        raster_crs = src.crs

    # Create a bounding box polygon from the raster bounds
    bbox = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

    # Create a GeoDataFrame for the bounding box
    bbox_gdf = gpd.GeoDataFrame({"geometry": [bbox]}, crs=raster_crs)

    # Reproject the bounding box to the shapefile's CRS if needed
    if gdf.crs is not None and gdf.crs != bbox_gdf.crs:
        bbox_gdf = bbox_gdf.to_crs(gdf.crs)

    # Create the plot
    _, ax = plt.subplots(figsize=(10, 10))
    # geopandas-stubs reject plain color names, though matplotlib accepts them
    gdf.plot(ax=ax, facecolor="none", edgecolor="blue", linewidth=1)  # ty: ignore[invalid-argument-type]
    bbox_gdf.boundary.plot(ax=ax, color="red", linewidth=2)  # ty: ignore[invalid-argument-type]
    ax.set_title("Shapefile (blue) with Raster Bounds (red)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.show()


if __name__ == "__main__":
    # ------ Please change the paths to your local paths ------
    # Define file paths and buffer distance
    # Shapefiles can be downloaded from https://www.marineregions.org/gazetteer.php/gazetteer.php?p=details&id=1905
    fp_shp = Path("src/resources/download_images/iho.shp")
    fp1 = Path("src/resources/download_images/S2A_OPER_MSI_L2A_TL_2APS_20230130T142458_A039730_T33TWJ_N05.09.tif")
    fp2 = fp1.with_name(f"{fp1.stem}_mask.tif")
    fp3 = fp1.with_name(f"{fp1.stem}_SeaOnly.tif")

    print("---------- Inspecting Shapefile ----------")
    plot_shp_and_raster_bounds(fp_shp, fp1)
    plt.savefig("src/resources/download_images/test1.png", bbox_inches="tight")
    plt.close()
    print("---------- Inspecting Mask ----------")
    inspect_fp(fp2)
    plt.savefig("src/resources/download_images/test2.png", bbox_inches="tight")
    plt.close()
    print("---------- Inspecting Original ----------")
    inspect_fp(fp1)
    plt.savefig("src/resources/download_images/test3.png", bbox_inches="tight")
    plt.close()
    print("---------- Inspecting Sea Only ----------")
    inspect_fp(fp3)
    plt.savefig("src/resources/download_images/test4.png", bbox_inches="tight")
    plt.close()
