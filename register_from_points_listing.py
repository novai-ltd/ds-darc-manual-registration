import numpy as np
import cv2
import glob
import os
import sys
import json
import pandas as pd
import PySide2
import time
import SimpleITK as sitk
from pathlib import Path
from os.path import join, basename
from skimage.color import rgb2gray
from PyAppSelectPoints_pyside import standard_image_read

def register_images_from_points_listing(points_listing_filepath, resampled_image_dir=None, create_masks=None, masks_dir=None):

    # open the points listing file
    points_listing_df = pd.read_csv(points_listing_filepath)

    # loop through the points listing dataframe
    for index, row in points_listing_df.iterrows():

        # get everything we need from the row
        target_image_dir = row["target image directory"]
        target_image_filename = row["target image file"]
        moving_image_dir = row["moving image directory"]
        moving_image_filename = row["moving image file"]
        target_point_1 = eval(row["target 1"])
        target_point_2 = eval(row["target 2"])
        target_point_3 = eval(row["target 3"])
        moving_point_1 = eval(row["moving 1"])
        moving_point_2 = eval(row["moving 2"])
        moving_point_3 = eval(row["moving 3"])
        #
        # create numpy arrays from the points
        target_points = np.array([target_point_1, target_point_2, target_point_3])
        moving_points = np.array([moving_point_1, moving_point_2, moving_point_3])

        # calculate the affine transformation matrix
        transformation_matrix = cv2.getAffineTransform(moving_points.astype(np.float32), target_points.astype(np.float32))

        # read in both images
        target_img = standard_image_read(join(target_image_dir, target_image_filename))
        moving_img = standard_image_read(join(moving_image_dir, moving_image_filename))

        # resample moving image according to transformation, to size of target image
        target_size = target_img.shape
        resampled_img = cv2.warpAffine(moving_img, transformation_matrix, target_size)

        # Convert grayscale to RGB so macOS Preview shows it properly
        resampled_img = np.clip(resampled_img * 255, 0, 255).astype(np.uint8)
        resampled_img = cv2.cvtColor(resampled_img, cv2.COLOR_GRAY2RGB)

        # save the resampled image
        moving_image_stem = Path(moving_image_filename).stem
        registered_image_filename = f"{moving_image_stem}_registered_manual.tif"
        if resampled_image_dir is None:
            registered_image_filepath = join(moving_image_dir, registered_image_filename)
        else:
            registered_image_filepath = join(resampled_image_dir, registered_image_filename)
        cv2.imwrite(registered_image_filepath, resampled_img)








