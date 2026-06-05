import argparse
import json
from os.path import basename, join, dirname

import numpy as np
import cv2
import pandas as pd

def transform_point(transformation_matrix, point):

    # convert point to a numpy array of shape (1, 1, 2) for cv2.transform
    point_array = np.array([[[point["x"], point["y"]]]])

    # transform the point using the transformation matrix
    transformed_point = cv2.transform(point_array, transformation_matrix)
    return transformed_point

def transform_points_in_file(transformation_matrix_filepath, native_spot_locations_filepath, transformed_points_dir=None):

    # read transformation matrix into numpy array
    transformation_matrix = np.loadtxt(transformation_matrix_filepath)

    # start list of transformed points
    transformed_points = []

    # read in the points file from JSON file
    with open(native_spot_locations_filepath, 'r') as f:

        points_data_dict = json.load(f)

    # extract points from the dictionary and initialize list of new points
    points = points_data_dict["spot_coordinates"]

    # transform points one by one
    # append transformed points to list as dicts
    for point in points :

        transformed_point = transform_point(transformation_matrix, point)
        transformed_points.append({"x": transformed_point[0][0][0], "y": transformed_point[0][0][1]})

    # replace old coordinates with new in points_data_dict
    # replace both original scale as well as scale is arbitrary anyway
    points_data_dict.update({"spot_coordinates_registered_space": transformed_points, "spot_coordinates_registered_space_original_scale": transformed_points})

    # generate new filename for registered spot location file
    transformed_points_listing_filename = basename(native_spot_locations_filepath).replace(".json", "_registered.json")

    # generate filepath for registered spot location file
    # if no directory given write into same dir as read from
    # then save again as JSON file
    if transformed_points_dir is None :
        transformed_points_dir = dirname(native_spot_locations_filepath)
    transformed_points_listing_filepath = join(transformed_points_dir, transformed_points_listing_filename)
    with open(transformed_points_listing_filepath, 'w') as fp:
        json.dump(points_data_dict, fp)

def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--transformation_matrix")
    parser.add_argument("--native_spot_locations_file")
    parser.add_argument("--transformed_points_dir", default=None)

    args = parser.parse_args()

    transform_points_in_file(
        args.transformation_matrix,
        args.native_spot_locations_file,
        args.transformed_points_dir)

if __name__ == "__main__":
    main()







