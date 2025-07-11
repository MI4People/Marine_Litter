import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import box
import numpy as np

def shp_to_tif(fp_shp, fp1, out_tif, buffer_meter=0):
    """
    Reprojects a shapefile to the CRS of fp1, applies a buffer (in meters) to the geometries,
    clips it to fp1's extent, and rasterizes it using fp1's exact grid specifications (resolution, bounds, and dimensions).

    Parameters:
      fp_shp (str): File path to the input shapefile.
      fp1 (str): File path to the reference GeoTIFF (defines CRS, bounds, and grid).
      out_tif (str): Output file path for the resulting rasterized GeoTIFF.
      buffer_meter (float): Buffer distance in meters to apply to the geometries (default: 0). 
        Positive values moves the goemetry inland, negative values are not recommended.
        This is to avoid edge effects when rasterizing.
        The buffer is applied before clipping to fp1's extent.
    
    Returns:
      str: The output file path of the rasterized GeoTIFF.
    """
    # Open fp1 to get grid specifications
    with rasterio.open(fp1) as src_fp1:
        fp1_bounds = src_fp1.bounds
        fp1_transform = src_fp1.transform
        fp1_width = src_fp1.width
        fp1_height = src_fp1.height
        target_crs = src_fp1.crs
        fp1_meta = src_fp1.meta.copy()
    
    # Load the shapefile
    gdf = gpd.read_file(fp_shp)
    
    # Reproject the shapefile to the target CRS if needed
    if gdf.crs != target_crs:
        gdf = gdf.to_crs(target_crs)
    
    # Apply buffer (in meters) if specified
    if buffer_meter != 0:
        gdf['geometry'] = gdf.geometry.buffer(buffer_meter)
    
    # Clip the shapefile to the extent of fp1
    fp1_box = box(fp1_bounds.left, fp1_bounds.bottom, fp1_bounds.right, fp1_bounds.top)
    gdf_clipped = gpd.clip(gdf, fp1_box)
    
    # Prepare shapes for rasterization (burn value 1 where geometry exists)
    shapes = ((geom, 1) for geom in gdf_clipped.geometry) if not gdf_clipped.empty else []
    
    # Rasterize using fp1's grid specifications
    raster = rasterize(
        shapes=shapes,
        out_shape=(fp1_height, fp1_width),
        transform=fp1_transform,
        fill=0,
        dtype=np.uint8
    )
    
    # Update metadata for output
    fp1_meta.update({
        'driver': 'GTiff',
        'height': fp1_height,
        'width': fp1_width,
        'count': 1,
        'dtype': np.uint8,
        'transform': fp1_transform,
        'crs': target_crs
    })
    
    # Write the rasterized shapefile to GeoTIFF
    with rasterio.open(out_tif, 'w', **fp1_meta) as dst:
        dst.write(raster, 1)
    
    return out_tif

def mask_fp1_using_fp2(fp1, fp2, out_fp):
    """
    Masks out parts of fp1 where fp2 indicates land across all bands.
    For each pixel in fp1, if the corresponding pixel in fp2 is 0 (land),
    then that pixel in every band of fp1 is set to 0.
    
    Parameters:
      fp1 (str): File path to the input GeoTIFF (e.g., SatelliteIMG with 12 bands).
      fp2 (str): File path to the mask GeoTIFF (rasterized shapefile, single band).
      out_fp (str): File path for the output masked GeoTIFF.
    
    Returns:
      str: The output file path.
    """
    # Read all bands from the original tif
    with rasterio.open(fp1) as src1:
        fp1_data = src1.read()  # shape: (bands, height, width)
        meta = src1.meta.copy()
        original_band_count = src1.count  # original number of bands
    
    # Read the single-band mask tif
    with rasterio.open(fp2) as src2:
        fp2_data = src2.read(1)  # shape: (height, width)
    
    # Check that the spatial dimensions match
    if fp1_data.shape[1:] != fp2_data.shape:
        raise ValueError("fp1 and fp2 have different spatial dimensions. They must be aligned.")
    
    # Apply the mask to all bands using broadcasting.
    # This will set the pixel to 0 in every band where fp2 is 0.
    masked_fp1 = fp1_data.copy()
    masked_fp1[:, fp2_data == 0] = 0

    # Write the masked output using the original metadata (which preserves the band count)
    with rasterio.open(out_fp, 'w', **meta) as dst:
        dst.write(masked_fp1)
    
    # Optionally, verify the number of bands in the output file
    with rasterio.open(out_fp) as result:
        final_band_count = result.count
        print(f"Original band count: {original_band_count}")
        print(f"Final band count: {final_band_count}")

    return out_fp

if __name__ == '__main__':
    # ------ Please change the paths to your local paths ------
    # Define file paths and buffer distance
    # Shapefiles can be downloaded from https://www.marineregions.org/gazetteer.php/gazetteer.php?p=details&id=1905
    fp_shp = r'src/resources/download_images/iho.shp'
    fp1 = r'src/resources/download_images/SatelliteIMG.tif'
    fp2 = fp1.replace(".tif", "_mask.tif")
    fp3 = fp1.replace(".tif", "_SeaOnly.tif")
    LandmassenBuffer = 250 # durch Ungenauikeit der Shapefile, Verschiebung der Landmassen vom Wasser weg um x Meter

    # Convert shapefile to raster
    print("Converting shapefile to raster (fp2)...")
    shp_to_tif(fp_shp, fp1, fp2, LandmassenBuffer)
    print(f"Rasterized shapefile saved as: {fp2}")

    # Mask fp1 using fp2 to obtain sea-only image
    print("Masking fp1 using fp2 to obtain sea-only image (fp3)...")
    mask_fp1_using_fp2(fp1, fp2, fp3)
    print(f"Sea-only image saved as: {fp3}")