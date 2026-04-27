# Manual registration tool

The spot labeller app is a simple GUI tool to enable a user to manually mark points on pairs of images so one image of the pair
(the moving image) can be registered to the other (the target image). If the points are at anatomically corresponding points,
then with three point pairs we can calculate an affine transform mapping the points on the moving image to those on the target image.
This transform is then applied to the whole moving image and it can be resampled to align it with the target image.
The app facilitates this by displaying the images in a pair side-by-side, allowing you to add, delete and save points pairs,
and calculate a transform and resample the moving image all in a single place.
## Installation

### Install Python code

The labeller app is written in Python and uses the PyQt5 library for the GUI. To obtain the code, clone the Git repository at https://github.com/novai-ltd/ds-darc-manual-registration.git.
After cloning, open the Anaconda command line tool and cd to the ds-darc-manual-registration directory. Create a conda environment for the app, activate the environment
and install the required packages with the provided requirements.txt file.
```
conda create -n manual_registration_app python=3.10
conda activate manual_registration_app
pip install -r requirements.txt
```

Unlike other apps, there are currently no compiled executable versions of the manual registration tool; however they may be made available in future. 

## Usage

### Directory structure and set up

The app is configured by calling the RunAppManualRegistration script with a set of parameters. There is
no required folder structure for the images. The parameters are as follows:

#### Required parameters
Three parameters are required to be set:

* registration_files_list. This is the path of a csv file listing the paths of the moving and target image files, and other optional information.
* upload_name. This is a string prepended to the filename of the list of points, to identify this experiment or run of registrations.
* session_registration_dir. This is the path of a directory where the registration points for all images are saved to file, both as .csv and pickle.

#### Optional parameters
Two optional parameters allow the user to set default directories for resampled images (if any) and resample masks (if any). These can
be overridden on a per-registration basis by including the relevant columns in the registration files list csv, as described below.

* --resampled_image_dir. Save resampled images to this directory, for registrations where the files list specifies that the moving image should be resampled but does not specify a directory to save the resampled image to.
If the directory is set in neither place, resampled images will be saved to the same directory as the moving image they were created from.
* --resampled_mask_dir. Save resampled_masks to this directory, for registrations where the files list specifies that a mask should be created but does not specify a directory to save the mask to. 
  If the directory is set in neither place, masks will be saved to the same directory as the moving image they were created from.

an example registration_files_list csv file is provided in the repo, which can be copied and edited to create a files list for your set of registrations.



#### Registration files list
This must be a csv file with the following column names: "target image file", "moving image file", "target image directory", "moving image directory".
Each row will represent a pair of images for registration. The "target image file" and "moving image file" cells should contain the file names of the moving image 
to be registered, and the target image for it to be registered to respectively. The "target image directory" and "moving image directory" cells should contain the
paths to the directories containing the target image file and moving image file respectively. This means that the image files can be in any directory or combinbation of directories;
however in practice it may be better to put all of the images in a single directory, or for there to be one directory for all target images and one for all moving
images. A template file is provided in the repo which can be copied to form a file for your set of registrations. In many cases multiple moving images may be 
registered to the same target image, in which case the "target image file" will be repeated across lines.

#### Optional columns in files list
More control over the extra outputs of the app can be achieved by adding extra columns to the registration files list csv.
In general, the optional columns are applied on a per-registration basis: they can be left out entirely (in which case the app will use default settings for all registrations), 
or they can be included and filled in for some registrations but not others (in which case the app will use the specified settings for those registrations, and default settings for the rest

The following optional columns can be added:
* registration_dir. This column can contain paths to directories to save the transformation matrix for each registration. If this column is not included, the matrices will be
saved to the session_registration_dir. If this column is included but some rows are left blank, the matrices for those rows will be saved to the session_registration_dir.
* resample_image. This column can be set to TRUE or FALSE to specify whether the moving image for each registration should be resampled by the app. If this column is not included, the app will use the default setting for all registrations (which is not to resample). 
  If this column is included but some rows are left blank, the app will use the default setting for those rows (which is not to resample). 
* resampled_image_dir. This column can contain paths to directories to save the resampled images for each registration. This is ignored if resample_image is not set to TRUE.
  If not included or for rows where it is left blank, the resampled image are written to the optional registered_image_dir command line argument if that is set, or else the directory of the moving image. 
* create_mask. This column can be set to TRUE or FALSE to specify whether a binary mask should be created by the app for each registration. If this column is not included, the app will use the default setting for all registrations (which is not to create masks). 
  If this column is included but some rows are left blank, the app will use the default setting for those rows (which is not to resample).
* resampled_mask_dir. This column can contain paths to directories to save the resampled masks for each registration. This is ignored if create_mask is not set to TRUE.
If not included or for rows where it is left blank, the resampled masks are written to the optional registered_mask_dir command line argument if that is set, or else the directory of the moving image.
  
  
### Running the app
To run the app in Python, simply call the RunAppManualRegistration script with the following command and arguments:

```
python RunAppManualRegistration.py path/to/registration_files_list_csv upload_name path/to/registration_directory
[--resampled_image_dir path/to/resampled_image_dir] [--resampled_mask_dir path/to/resampled_mask_dir]
```

For example, to run the app and provide a default location for any resampled images and masks, the command would look like this:

```
python RunAppManualRegistration.py path/to/registration_files_list_csv experiment_01 path/to/registration_directory --resampled_image_dir path/to/resampled_image_dir --resampled_mask_dir path/to/resampled_mask_dir
```

The same script can also be run from your IDE.

### Using the app

#### App layout
The app presents the user with a pair of images: the target image on the left and the moving image on the right. Above
each image is a pair of buttons to control the zoom, and stretching underneath both is a dropdown menu to select an image pair.
On the right hand side of the images is a table showing the locations of saved points, with buttons underneath to control
saving, deleting and writing points.

#### Placing points and zooming

Place points on the images by left clicking with the mouse. Until a pair of points is added, the current points can be moved
as many times as the user likes by left clicking the relevant image in a new location. To more precisely place spots, you can zoom in on an area of the image.
This is done by clicking the right mouse button and dragging the mouse with the button held down. The selected area will be outlined
on the image and will move with the mouse while the right button is held down. The area is forced to be square (by taking the minimum
of the height and width of the rectangle defined by the initial right click and the current cursor position) and is restricted to the image 
boundaries even if the cursor goes outside. You can zoom in multiple times, but the zoom will not be allowed if the selected
area is below a set size. Click the undo zoom button to go back to the previous zoom level, and reset zoom to go back to fully
zoomed out. When you zoom in or out, all the existing points are redrawn in the correct position in the zoomed view, including
no longer being shown if they are outside of the new view when zooming in. Keyboard shortcuts are also available for undoing and 
resetting zoom: 'ctrl+b' for undo zoom on moving image, 'shift+b' for undo zoom on target image, 'ctrl+r' for reset zoom on moving image, 'shift+r' for reset zoom on target image.

#### Adding and saving point pairs

When you are happy with the placement of points in corresponding locations in the moving and target image, click add point pair
and the positions of the point pair will be locked. The coordinates of the spots in the pixel coordinate system of the original
image will appear in the added points table. The process can then be repeated to add another pair of spots; notice that each
pair of points is shown in a different colour so it can be clearly seen which point on the target image is paired with which 
point on the moving image. When three point pairs have been added, that is sufficient to calculate a transform. The save current point
pairs button will then be enabled, which writes the three point pairs to the internal database. Keyboard shortcuts are also available for adding and saving point pairs:
'a' for add a point pair, and 's' for save current point pairs (with no modifiers). The keyboard shortcuts will only work when the app state allows the action to be done
and the associated button is enabled.

At any point where one or more point pairs has been added, the remove all points button will be enabled. Clicking it will remove *all* the point pairs
for this pair of images. It is not currently possible to remove only the most recently added pair of points, or to specify
a particular pair to remove. This facility may be made available in future; in the meantime it is advised to carefully
check the placement of a point pair before adding them.

##### Choosing a new image pair

If no point pairs have been added, or all three have been added and saved, the dropdown menu for selecting a new image pair
is enabled. Use this to move on to a new image pair when the current one has been finished, or to peek ahead. You can always navigate back
to an image a second time and the saved points will be shown and can be revised, but only by removing the point pairs as
described in the previous section. Image pair selection can also be done using the keyboard shortcuts right and left arrow keys
for next and previous image pair respectively. The keyboard shortcuts will only work when the app state allows the action to be done and the 
dropdown menu is enabled. Selecting previous when at the first image pair, or next when at the last image pair, will have no effect, i.e. 
there is no 'wrapping round' between the first and last image pairs.

#### Saving the transformations

When three point pairs have been saved for all the image pairs listed in the registration files list, the write saved points 
to file and quit button is enabled. When pressed, this will save to disk the default outputs of a transformation matrix file for each image,
and a single file containing the point pair locations for all image pairs. If the options to save the resampled images and/or the
image masks were turned on, these will be saved also.

### Guidance on point placement

Points should be placed on anatomically identical locations on the target and moving image. What this means is context dependent,
but generally intersections of prominent blood vessels are used as such locations. Generally, where possible the points should be placed
as far as possible apart from each other on each image as this leads to less error in calculating the registration transform. However this 
must be balanced against the need to clearly identify corresponding locations; in particular if one or both images in a pair
are of poor quality or the images' fields of view do not overlap much there may be very little choice of clearly identifiable locations.

## Generating resampled images from a script

The script register_from_points_listing.py can be used to generate resampled images, and optionally mask images, if the 
app was run to mark points but had the resampling and mask options turned off. It does this by reading in the file created by
reading containing the point pair locations that is always created by the app, and regenerating the transformations.
#### Required arguments

The script requires the following arguments:

* points_listing_file: full filepath to the points listing pickle (.pkl) file created by the app
* transformation_dir: path of directory to write the generated transformation matrices to

There are are also three optional arguments:

* resampled_image_dir: path of directory to save the resampled images in. Defaults to the moving image
directory for each registration if not set
* create_masks: if set, create resampled image masks. If not set, no masks will be created
* mask_dir: path of directory to write masks to, if create_masks is set. If create_masks is set but mask_dir is not
provided, it also defaults to the moving image directory for each registration.
  
resampled image files and resampled mask files have "registered_manual" and "registered_mask_manual" appended
onto the stem of moving image file names, so the original moving image files cannot be overwritten.

so and example usage, if we want to generate masks and provide non-default directories for both resampled
images and masks might be

```
python register_from_points_listing.py --points_listing_file path/to/points/file.pkl --transformation_dir path/to/transform dir --resampled_image_dir path/to/resampled/dir --create_masks --mask_dir path/to/mask/dir
```

The script also generates and saves an enhanced version of the points listing file. This has the same
name as the points listing file with '_registered_details' appended to the filename stem, and is saved in the same directory.
It adds paths to transformation matrix files and resampled image files, and to mask files if they were generated.