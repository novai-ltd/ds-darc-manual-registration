from AppManualRegistration import call_app

# set required parameters:
# directory to write points and transformations to
registration_dir = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\transformation_files"
# stem for points filename
upload_name = "test"
# path to read list of registration files from
registration_files_list = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\manual_registration_files.csv"

# set optional parameters:
# flag whether to resample images and directory to save resampled images to if yes
resample_images = True
resampled_image_dir = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\resampled_images"
# flag whether to create mask image and directory to save mask images to if yes
create_masks = True
resampled_mask_image_dir = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\resampled_masks"

# run the app with the parameters you have set
call_app(registration_dir, upload_name, registration_files_list, resample_images=resample_images, resampled_image_dir=resampled_image_dir, create_masks=create_masks, mask_dir=resampled_mask_image_dir)
print('done!')

