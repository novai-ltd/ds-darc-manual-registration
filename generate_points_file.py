import pandas as pd
import numpy as np


# read in original points file
points_data = pd.read_csv("C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\transformation_files\\test_manual_registration_points.csv")

# start list for new points
target_image_points_1 = []
moving_image_points_1 = []
target_image_points_2 = []
moving_image_points_2 = []
target_image_points_3 = []
moving_image_points_3 = []

# loop though each row
for index, row in points_data.iterrows():
    target_image_points = eval(row['target image points'])
    moving_image_points = eval(row['moving image points'])
    target_image_scale = eval(row['target image scale factors'])
    moving_image_scale = eval(row['moving image scale factors'])

    # loop through each point pair
    for point_index, target_image_point in enumerate(target_image_points):

        # get the corresponding moving image point
        moving_image_point = moving_image_points[point_index]

        # scale the points
        scaled_target_image_point = (target_image_point[0] * target_image_scale[0], target_image_point[1] * target_image_scale[1])
        scaled_moving_image_point = (moving_image_point[0] * moving_image_scale[0], moving_image_point[1] * moving_image_scale[1])

        # append to the new lists
        if point_index == 0:
            target_image_points_1.append(scaled_target_image_point)
            moving_image_points_1.append(scaled_moving_image_point)
        elif point_index == 1:
            target_image_points_2.append(scaled_target_image_point)
            moving_image_points_2.append(scaled_moving_image_point)
        elif point_index == 2:
            target_image_points_3.append(scaled_target_image_point)
            moving_image_points_3.append(scaled_moving_image_point)

# add new columns to the dataframe
points_data['target 1'] = target_image_points_1
points_data['moving 1'] = moving_image_points_1
points_data['target 2'] = target_image_points_2
points_data['moving 2'] = moving_image_points_2
points_data['target 3'] = target_image_points_3
points_data['moving 3'] = moving_image_points_3

# select only columns of interest and save
points_data = points_data[['target image file', 'moving image file', 'target image directory', 'moving image directory', 'target 1', 'moving 1', 'target 2', 'moving 2', 'target 3', 'moving 3']]
points_data.to_csv("C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\points_list_native_scale.csv", index=False, header=True)
