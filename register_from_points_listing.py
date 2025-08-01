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

def parse_point_pair(point_pair_str):

    # strip the string of whitespace and parentheses
    point_pair_str = point_pair_str.strip("()")
    point_pair_str = point_pair_str.replace(" ", "")

    # split the string by commas and convert to a tuple of floats
    point_pair_list = point_pair_str.split(",")
    point_pair_tuple = tuple(float(coord) for coord in point_pair_list)
    return point_pair_tuple

def register_images_from_points_listing(points_listing_filepath, transformation_dir, resampled_image_dir=None, create_masks=None, mask_dir=None):

    # open the points listing file
    points_listing_df = pd.read_csv(points_listing_filepath)

    # initialize lists to hold the paths of the transformation matrices and resampled images
    # and optionally the masks
    transformation_matrix_filepaths = []
    resampled_image_filepaths = []
    if create_masks:
        mask_filepaths = []

    # loop through the points listing dataframe
    for index, row in points_listing_df.iterrows():

        # get everything we need from the row
        target_image_dir = row["target image directory"]
        target_image_filename = row["target image file"]
        moving_image_dir = row["moving image directory"]
        moving_image_filename = row["moving image file"]
        target_point_1 = parse_point_pair(row["target 1"])
        target_point_2 = parse_point_pair(row["target 2"])
        target_point_3 = parse_point_pair(row["target 3"])
        moving_point_1 = parse_point_pair(row["moving 1"])
        moving_point_2 = parse_point_pair(row["moving 2"])
        moving_point_3 = parse_point_pair(row["moving 3"])

        # create numpy arrays from the points
        target_points = np.array([target_point_1, target_point_2, target_point_3])
        moving_points = np.array([moving_point_1, moving_point_2, moving_point_3])

        # calculate the affine transformation matrix
        transformation_matrix = cv2.getAffineTransform(moving_points.astype(np.float32), target_points.astype(np.float32))

        # save homogenous transformation matrix, append paths to lists
        moving_image_stem = Path(moving_image_filename).stem
        transformation_matrix_filepath = os.path.join(transformation_dir, f"{moving_image_stem}_transformation_matrix.txt")
        np.savetxt(transformation_matrix_filepath, transformation_matrix)
        transformation_matrix_filepaths.append(transformation_matrix_filepath)

        # read in both images
        target_img = standard_image_read(join(target_image_dir, target_image_filename))
        moving_img = standard_image_read(join(moving_image_dir, moving_image_filename))

        # resample moving image according to transformation, to size of target image
        target_size = target_img.shape
        resampled_img = cv2.warpAffine(moving_img, transformation_matrix, target_size)

        # Convert grayscale to RGB so macOS Preview shows it properly
        resampled_img = np.clip(resampled_img * 255, 0, 255).astype(np.uint8)
        resampled_img = cv2.cvtColor(resampled_img, cv2.COLOR_GRAY2RGB)

        # create a mask if requested
        if create_masks:

            # create mask of moving image
            # ones to match moving image size
            # resample moving image according to transformation, to size of target image
            mask_img = np.ones_like(moving_img)
            resampled_mask_img = cv2.warpAffine(mask_img, transformation_matrix, target_size)

            # Convert grayscale to RGB so macOS Preview shows it properly
            resampled_mask_img = np.clip(resampled_mask_img * 255, 0, 255).astype(np.uint8)
            resampled_mask_img = cv2.cvtColor(resampled_mask_img, cv2.COLOR_GRAY2RGB)

            # save registered mask
            # if no directory is given save in same directory as moving image
            # otherwise save in specified directory
            registered_mask_image_filename = f"{moving_image_stem}_registered_mask_manual.tif"
            if mask_dir is None:
                registered_mask_image_filepath = join(moving_image_dir, registered_mask_image_filename)
            else:
                registered_mask_image_filepath = join(mask_dir, registered_mask_image_filename)
            cv2.imwrite(registered_mask_image_filepath, resampled_mask_img)

            # append mask filepath to list
            mask_filepaths.append(registered_mask_image_filepath)

        # save the resampled image
        registered_image_filename = f"{moving_image_stem}_registered_manual.tif"
        if resampled_image_dir is None:
            registered_image_filepath = join(moving_image_dir, registered_image_filename)
        else:
            registered_image_filepath = join(resampled_image_dir, registered_image_filename)
        cv2.imwrite(registered_image_filepath, resampled_img)

    foo=1








