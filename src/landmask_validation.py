import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from shapely.geometry import box

def inspect_fp(fp1):
    """
    Inspect a raster file and display its metadata and a false color composite.
    Parameters:
        fp1 (str): Path to the raster file.
    """
    with rasterio.open(fp1) as src:
        print("Number of bands:", src.count)
        print("CRS:", src.crs)
        print("Bounds:", src.bounds)
        print("Transform:", src.transform)
        data = src.read()  # Reads all bands; shape: (bands, height, width)
        print("Data shape:", data.shape)
        
        # Helper function to normalize an array to [0, 1]
        def normalize(arr):
            if arr.max() > arr.min():
                return (arr - arr.min()) / (arr.max() - arr.min())
            return arr
        
        # Create a compound false color composite using all bands
        def create_false_color(data):
            n_bands, height, width = data.shape
            if n_bands == 3:
                # If exactly three bands, use them directly as RGB
                r = normalize(data[0])
                g = normalize(data[1])
                b = normalize(data[2])
                return np.dstack((r, g, b))
            else:
                # Cycle through bands and assign to R, G, B channels
                R = np.zeros((height, width), dtype=np.float32)
                G = np.zeros((height, width), dtype=np.float32)
                B = np.zeros((height, width), dtype=np.float32)
                count_R = count_G = count_B = 0
                for i in range(n_bands):
                    norm_band = normalize(data[i])
                    if i % 3 == 0:
                        R += norm_band
                        count_R += 1
                    elif i % 3 == 1:
                        G += norm_band
                        count_G += 1
                    else:
                        B += norm_band
                        count_B += 1
                if count_R > 0: R /= count_R
                if count_G > 0: G /= count_G
                if count_B > 0: B /= count_B
                return np.dstack((R, G, B))
        
        # Build a list of images and corresponding titles for plotting
        images = []
        titles = []
        
        # Only add the false color composite if more than one band exists
        if src.count > 1:
            composite_false = create_false_color(data)
            images.append(composite_false)
            titles.append("Composite False Color")
        
        # Add the true color composite if at least three bands exist
        if src.count >= 3:
            true_r = normalize(data[0])
            true_g = normalize(data[1])
            true_b = normalize(data[2])
            true_color = np.dstack((true_r, true_g, true_b))
            images.append(true_color)
            titles.append("True Color")
        
        # Add each individual band in grayscale
        for i in range(src.count):
            images.append(normalize(data[i]))
            titles.append(f"Band {i+1}")
        
        total_images = len(images)
        fig, axs = plt.subplots(1, total_images, figsize=(5 * total_images, 5))
        if total_images == 1:
            axs = [axs]  # Ensure axs is iterable
        
        for ax, img, title in zip(axs, images, titles):
            # If image has three channels, display as is; otherwise use a grayscale colormap.
            if img.ndim == 3 and img.shape[2] == 3:
                ax.imshow(img)
            else:
                ax.imshow(img, cmap='gray')
            ax.set_title(title)
            ax.axis('off')
        
        plt.tight_layout()
        plt.show()

def plot_shp_and_raster_bounds(fp_shp, fp_tif):
    """
    Plots a shapefile with a red rectangle representing the bounds of a GeoTIFF raster.

    Parameters:
        fp_shp (str): Path to the shapefile.
        fp_tif (str): Path to the raster (GeoTIFF) file.
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
    bbox_gdf = gpd.GeoDataFrame({'geometry': [bbox]}, crs=raster_crs)

    # Reproject the bounding box to the shapefile's CRS if needed
    if gdf.crs != bbox_gdf.crs:
        bbox_gdf = bbox_gdf.to_crs(gdf.crs)

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 10))
    gdf.plot(ax=ax, facecolor='none', edgecolor='blue', linewidth=1)
    bbox_gdf.boundary.plot(ax=ax, color='red', linewidth=2)
    ax.set_title("Shapefile (blue) with Raster Bounds (red)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    plt.show()

if __name__ == '__main__':
    # ------ Please change the paths to your local paths ------
    # Define file paths and buffer distance
    # Shapefiles can be downloaded from https://www.marineregions.org/gazetteer.php/gazetteer.php?p=details&id=1905
    fp_shp = r'src/resources/download_images/iho.shp'
    fp1 = r'src/resources/download_images/S2A_OPER_MSI_L2A_TL_2APS_20230130T142458_A039730_T33TWJ_N05.09.tif'
    fp2 = fp1.replace(".tif", "_mask.tif")
    fp3 = fp1.replace(".tif", "_SeaOnly.tif")
    
    print("---------- Inspecting Shapefile ----------")
    plot_shp_and_raster_bounds(fp_shp, fp1)
    plt.savefig('src/resources/download_images/test1.png', bbox_inches='tight')
    plt.close()
    print("---------- Inspecting Mask ----------")
    inspect_fp(fp2)
    plt.savefig('src/resources/download_images/test2.png', bbox_inches='tight')
    plt.close()
    print("---------- Inspecting Original ----------")
    inspect_fp(fp1)
    plt.savefig('src/resources/download_images/test3.png', bbox_inches='tight')
    plt.close()
    print("---------- Inspecting Sea Only ----------")
    inspect_fp(fp3)
    plt.savefig('src/resources/download_images/test4.png', bbox_inches='tight')
    plt.close()