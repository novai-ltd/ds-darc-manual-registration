#from PySide2 import QtCore, QtGui, QtWidgets
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
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

def standard_image_read(image_file_path) :
    """
    Read a .tif image into standard format for manipulation, a single channel image respresented a 2d numpy array
    of floats

    Args:
        image_file_path (string): path to .tif of image file

    Returns
        SITK transformation object and SITK registered image
    """

    # read in image from file
    image = cv2.imread(image_file_path)

    # handle potentially RGB or grayscale images
    if image.ndim == 2:
        image = image / 255.0
    elif image.ndim == 3:
        image = rgb2gray(image)
    return image

class QResizingPixmapLabel(QLabel):
    """
    Class extending QLabel to allow for resizing of the image while keeping the aspect ratio

    On resize, set new image size, widget size, and scale factor as attributes of the main window
    and redraw both images

    Attributes:
        main_window (MainWindow): main window of the application
    """

    def __init__(self, main_window):
        """
        Initialize the QLabel class
        Set initial parameters and pointer to main window

        Args:
            main_window (MainWindow): main window of the application
        Attributes:
            main_window (MainWindow): main window of the application
        """
        super().__init__()
        self.main_window = main_window
        self.setMinimumSize(1,1)
        self.setScaledContents(False)
        self._pixmap = QPixmap(self.pixmap())

    def heightForWidth(self, width):
        """
        Calculate the preferred height for this widget, given the width.

        Args:
            width (int): width of the widget
        Returns:
            int: height of the widget
        """
        if self._pixmap is None:
            return self.height()
        else:
            return int(width * (self.pixmap().height() / self.pixmap().width()))

    def setPixmap(self, pixmap):
        """
        set the Pixmap of the widget

        Args:
            pixmap (QPixmap): pixmap to set
        """
        self._pixmap = pixmap
        super().setPixmap(pixmap)

    def sizeHint(self):
        """
        suggest the size of the widget

        Returns:
            QSize: pyqt QSize object with the suggested height and width
        """

        # extract the width of the widget, and use it to calculate the height with heightForWidth
        width = self.width()
        return QSize(width, self.heightForWidth(width))

    # on resize, rescale the image to fit the label while keeping the aspect ratio
    def resizeEvent(self, event):
        """
        Handle a resize event.
        First calculate the new size of the image, then redraw both images at the new size
        Then set the new image and image widget size as attributes of the main window to enable correct spot removal and addition

        Args:
            event (QEvent): resize event
        """

        print("resize")
        if self._pixmap is not None:

            print("resize")

            # calculate the new size of the image
            scaled = self._pixmap.scaled(self.width(), self.height(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            image_height = scaled.height()
            image_width = scaled.width()


            # redraw both images
            self.main_window.set_original_moving_image()
            self.main_window.set_original_target_image()

            # reset the image and image widget size as attributes of the main window
            # and recalculate and store scale factor
            self.main_window.image_display_size = (image_height, image_width)
            self.main_window.image_widget_size = (self.width(), self.height())
            self.main_window.scale_factor = self.main_window.image_display_size[0] / self.main_window.current_moving_image_array_size[0]
            print(f"image_height = {image_height}")
            print(f"image_width = {image_width}")
            print(f"widget height: {self.height()}")
            print(f"widget width: {self.width()}")



            # set alignment of the image in the widget to center
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)


# For the migration from PyQt5 to PySide2 to work (on Mac at least), one must set this environment variable otherwise it hangs indefinitely (whereas it's fine in PyQt5)
# https://stackoverflow.com/questions/64833558/apps-not-popping-up-on-macos-big-sur-11-0-1#_=
# os.environ['QT_MAC_WANTS_LAYER'] = '1'

# Equivalent fix to the above on Windows is this
# thankyou to https://stackoverflow.com/questions/51367446/pyside2-application-failed-to-start
dirname = os.path.dirname(PySide2.__file__)
plugin_path = os.path.join(dirname, 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, registration_dir, upload_name, registration_files_csv, resample_images=True, resampled_image_directory=None, create_masks=False, mask_directory=None):
        super().__init__()

        # store paths to required and optional output directories, and flags for optional ones.
        self.set_paths(registration_dir, upload_name, resample_images, resampled_image_directory, create_masks, mask_directory)

        # read in any list of registration details to be done from .csv file
        self.set_alignments(registration_files_csv)

        # user selects alignments/image pairs from a pull down list widget
        # create the widget and populate the pull down list using file names from the alignments list
        self.create_alignment_selection_widget()

        # create the image display widgets
        self.set_up_image_display()

        # set up overall main window layout and connect controls to functions
        self.set_up_layout()
        self.connect_button_functionality()

        # set number of current points to 0
        self.current_n_points = 0

        # select first alignment by default
        self.select_alignment(self.widgetAlignmentSelection.itemText(0))


    def set_paths(self, registration_dir, upload_name, resample_images, resampled_image_directory, create_masks, mask_directory):

        """
        Takes the required and optional path arguments together with flags for whether the optional ones should be used
        and store so they can be accessed when needed later

        Args:
            registration_dir (str): string representing root directory of outputs to write registration details to
            upload_name (str): filename stem to use for file containing control point coordinates
            resample_images (bool): flag indicating whether to resample moving images to space of target images
            resampled_image_directory (str): path of directory to write resampled images to if resample_images = True
            create_masks (bool): flag indicating whether to generate binary masks showing the area covered by the moving image in the target space
            mask_directory (str): path of directory to write binary masks to if create_masks = True

        """

        # store details of where we will put output files
        self.base_dir = registration_dir
        self.upload_name = upload_name

        # store details of whether we want to resample images and if so where to save them to
        self.resample_images = resample_images
        self.resampled_image_directory = resampled_image_directory

        # similar for whether we want to create masks and if so where to save them
        self.create_masks = create_masks
        self.mask_directory = mask_directory

    def create_alignment_selection_widget(self):
        """
        The user selects which alignment/image pair to do by selecting from a dropdown list.
        Here we create a widget for that list, and then populate that list with image names pulled from the alignments table
        """

        # create the widget to hold the dropdown list
        self.widgetAlignmentSelection = QtWidgets.QComboBox(self)

        # loop through rows of the alignments table
        for i, row in enumerate(self.alignments.iterrows()):

            # for each row, join the name of the moving image to the name of the target image to create a dropdown menu item
            # then add the item to the widget
            alignment_txt = str(i+1) + ': ' + row[1][3] + ' to ' + row[1][2]
            self.widgetAlignmentSelection.addItem(alignment_txt)

        # connect the widget to the function implementing selection of an alignment/image pair
        self.widgetAlignmentSelection.activated[str].connect(self.select_alignment)

    def set_up_image_display(self):

        # set initial image size
        self.image_display_size = (1250, 1250)

        # create grey QPixmap to initially show before an alignment has been selected
        grey = QtGui.QPixmap(self.image_display_size[0], self.image_display_size[1])
        grey.fill(QtGui.QColor('darkGray'))

        # create QLabels/QResizingPixmapLabels for target and moving images
        #self.target_image = QtWidgets.QLabel(self)
        self.target_image = QResizingPixmapLabel(self)
        #self.moving_image = QtWidgets.QLabel(self)
        self.moving_image = QResizingPixmapLabel(self)

        # set the images to grey
        self.target_image.setPixmap(grey)
        self.moving_image.setPixmap(grey)

        # link mouse click on each image to function to place a point
        self.target_image.mousePressEvent = self.set_point_on_target_image
        self.moving_image.mousePressEvent = self.set_point_on_moving_image

    def set_alignments(self, registration_files_csv):

        """
        Read in a list of image pairs to be registered from file and store them

        Args:
            registration_files_csv (str): path to correctly formatted .csv file listing target image and moving image files and directories
        """

        # convert manual alignments to pandas DF
        # store with extra columns for added points
        # set extra columns as object as we want to put lists in them
        # first drop duplicates
        # check why this happens!!!
        self.alignments = pd.read_csv(registration_files_csv)
        self.alignments = self.alignments.drop_duplicates()
        self.alignments = self.alignments.reindex(
            columns=['target image directory', 'moving image directory', 'target image file', 'moving image file',
                     'target image points', 'moving image points', 'target image scale factors',
                     'moving image scale factors'])
        self.alignments[['target image points', 'moving image points', 'target image scale factors',
                         'moving image scale factors']] = self.alignments[
            ['target image points', 'moving image points', 'target image scale factors',
             'moving image scale factors']].astype('object')
        self.alignments[['target image points', 'moving image points', 'target image scale factors',
                         'moving image scale factors']] = self.alignments[
            ['target image points', 'moving image points', 'target image scale factors',
             'moving image scale factors']] = None
        self.n_alignments = len(self.alignments)
        self.n_alignments_done = 0

    def set_up_layout(self):

        """
        Create and organize the overall layout of the app elements
        Start with lowest level objects (except images, which are created in a separate function)
        Set appearance but not functionality of elements and hierarchically group them together to build top level layout

        """

        # set up text labels for images and point table
        # first create labels, then set label text and align them
        self.target_image_label = QtWidgets.QLabel(self)
        self.moving_image_label = QtWidgets.QLabel(self)
        self.point_table_label = QtWidgets.QLabel(self)
        self.target_image_label.setText('target image')
        self.moving_image_label.setText('moving image')
        self.point_table_label.setText('added points')
        self.target_image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.moving_image_label.setAlignment(QtCore.Qt.AlignCenter)
        self.point_table_label.setAlignment(QtCore.Qt.AlignCenter)

        # set up table to display coordinates of points added by the user
        # label the columns
        self.point_table = QtWidgets.QTableWidget()
        self.point_table.setRowCount(3)
        self.point_table.setColumnCount(2)
        self.point_table.setHorizontalHeaderLabels(["target image point", "moving image point"])

        # set up label for image selection dropdown list
        self.image_selection_label = QtWidgets.QLabel(self)
        self.image_selection_label.setText('image pair selection')
        self.image_selection_label.setAlignment(QtCore.Qt.AlignCenter)

        # set up point saving buttons
        # create BoxLayouto to put them in then create the buttons
        # adding button text to each one as we go
        # finally add the buttons to the layout
        self.layoutPointControl = QtWidgets.QVBoxLayout()
        self.add_points_button = QtWidgets.QPushButton(self)
        self.add_points_button.setText('add current point pair')
        self.save_points_button = QtWidgets.QPushButton(self)
        self.save_points_button.setText('save current points')
        self.remove_points_button = QtWidgets.QPushButton(self)
        self.remove_points_button.setText('remove all points')
        self.write_points_button = QtWidgets.QPushButton(self)
        self.write_points_button.setText('write saved points to file and quit')
        self.layoutPointControl.addWidget(self.point_table)
        self.layoutPointControl.addWidget(self.add_points_button)
        self.layoutPointControl.addWidget(self.save_points_button)
        self.layoutPointControl.addWidget(self.remove_points_button)
        self.layoutPointControl.addWidget(self.write_points_button)

        # set up overall layout with qgrid
        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.target_image_label, 0, 0)
        self.layout.addWidget(self.moving_image_label, 0, 1)
        self.layout.addWidget(self.point_table_label, 0, 2)
        self.layout.addWidget(self.target_image, 1, 0)
        self.layout.addWidget(self.moving_image, 1, 1)
        self.layout.addLayout(self.layoutPointControl, 1, 2)
        self.layout.addWidget(self.image_selection_label, 2, 0, 1, 2)
        self.layout.addWidget(self.widgetAlignmentSelection, 3, 0, 1, 2)

        # set overall layout as central widget
        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

    def connect_button_functionality(self):

        # connect point buttons to the appropriate functions
        self.add_points_button.clicked.connect(self.add_points)
        self.save_points_button.clicked.connect(self.save_points)
        self.remove_points_button.clicked.connect(self.remove_points)
        self.write_points_button.clicked.connect(self.write_points_to_file)

        # initially cannot add, save, write or remove points
        self.add_points_button.setDisabled(True)
        self.save_points_button.setDisabled(True)
        self.remove_points_button.setDisabled(True)
        self.write_points_button.setDisabled(True)

    # display eyes for selected alignment
    def select_alignment(self, alignment_str):

        # empty table
        self.point_table.clear()
        self.point_table.setHorizontalHeaderLabels(
            ["target image point", "moving image point"])

        # set current alignment
        self.current_alignment = alignment_str

        # look up current alignment in alignments table
        dummy_1, self.current_moving_image_file, dummy_2, self.current_target_image_file = alignment_str.split(' ')
        self.current_alignment_row = self.alignments.loc[(self.alignments['target image file'] == self.current_target_image_file) & (
            self.alignments['moving image file'] == self.current_moving_image_file)].head(1)

        self.current_alignment_row_index = self.current_alignment_row.index[0]

        self.current_target_image_dir = self.current_alignment_row['target image directory'].values[0]
        self.current_moving_image_dir = self.current_alignment_row['moving image directory'].values[0]

        # read and store image arrays
        self.current_moving_img_array = standard_image_read(join(self.current_moving_image_dir, self.current_moving_image_file))
        self.current_target_img_array = standard_image_read(join(self.current_target_image_dir, self.current_target_image_file))

        # store real image sizes so we can calculate scale factors after any resizing
        self.current_moving_image_array_size = self.current_moving_img_array.shape
        self.current_target_image_array_size = self.current_target_img_array.shape

        # add singleton dimension to images for channels
        self.current_target_img_array = self.current_target_img_array[:, np.newaxis]
        self.current_moving_img_array = self.current_moving_img_array[:, np.newaxis]

        # set images
        self.set_original_target_image()
        self.set_original_moving_image()

        # draw points if necessary
        # and repopulate table
        existing_target_image_points =  self.alignments.at[self.current_alignment_row_index, 'target image points']
        if not existing_target_image_points == None :

            existing_moving_image_points = self.alignments.at[self.current_alignment_row_index, 'moving image points']
            new_target_image = cv2.imread(os.path.join(self.current_target_image_dir, self.current_target_image_file))
            new_moving_image = cv2.imread(os.path.join(self.current_moving_image_dir, self.current_moving_image_file))

            current_points = []
            for i, target_image_point in enumerate(existing_target_image_points) :

                moving_image_point = existing_moving_image_points[i]
                point_pair = [target_image_point, moving_image_point]
                current_points.append(point_pair)
                colour = self.get_colour(i)
                new_target_image = cv2.resize(new_target_image, (self.image_size[0], self.image_size[1]))
                new_target_image = cv2.circle(new_target_image, (point_pair[0][0], point_pair[0][1]), 3, colour, -1)
                new_moving_image = cv2.resize(new_moving_image, (self.image_size[0], self.image_size[1]))
                new_moving_image = cv2.circle(new_moving_image, (point_pair[1][0], point_pair[1][1]), 3, colour, -1)

                self.point_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(point_pair[0])))
                self.point_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(point_pair[1])))

            self.current_points = current_points

            self.target_image.setPixmap(self.convert_ndarray_to_QPixmap(new_target_image))
            self.moving_image.setPixmap(self.convert_ndarray_to_QPixmap(new_moving_image))
            self.current_n_points = 3
            # turn off save button
            self.save_points_button.setDisabled(True)
            self.remove_points_button.setDisabled(False)

        else:

            self.remove_points_button.setDisabled(True)

            # initialise point storage
            self.current_points = []
            self.current_target_image_point = None
            self.current_moving_image_point = None

            # set number of current points to 0
            self.current_n_points = 0

    def write_points_to_file(self):

        # only enable if all points have been completed
        if self.n_alignments_done < self.n_alignments :

            QtWidgets.QMessageBox.about(self, "points warning", "Cannot save to file before all required points have been saved")

        # initialize lists of extra outputs: transformation matrix text files
        transformation_matrix_filenames = []

        # iterate through alignments generating a transformation matrix txt file and a sitk transformation object for each one
        for row in self.alignments.iterrows() :

            # extract:
            # target and moving points
            # target and moving scale factors
            moving_image_filename = row[1][3]
            target_points = row[1][4]
            moving_points = row[1][5]
            target_scale = row[1][6]
            moving_scale = row[1][7]

            # convert points to numpy arrays, allowing for scale
            target_points = np.array(target_points) * target_scale
            moving_points = np.array(moving_points) * moving_scale

            # generate homogenous transformation matrix
            transformation_matrix = cv2.getAffineTransform(moving_points.astype(np.float32), target_points.astype(np.float32))

            # save homogenous transformation matrix, append paths to lists
            moving_image_stem = Path(moving_image_filename).stem
            transformation_matrix_filename = os.path.join(self.base_dir, f"{moving_image_stem}_transformation_matrix.txt")
            np.savetxt(transformation_matrix_filename, transformation_matrix)
            transformation_matrix_filenames.append(transformation_matrix_filename)

            # if option is selected, apply transformation to moving image and save
            if self.resample_images :

                # get directories and target image filename
                target_image_dir = row[1][0]
                moving_image_dir = row[1][1]
                target_image_filename = row[1][2]

                # read in target and moving images
                moving_img = standard_image_read(join(moving_image_dir, moving_image_filename))
                target_img = standard_image_read(join(target_image_dir, target_image_filename))

                # resample moving image according to transformation, to size of target image
                target_size = target_img.shape
                resampled_img = cv2.warpAffine(moving_img,transformation_matrix,target_size)

                # Convert grayscale to RGB so macOS Preview shows it properly
                resampled_img = np.clip(resampled_img * 255, 0, 255).astype(np.uint8)
                resampled_img = cv2.cvtColor(resampled_img, cv2.COLOR_GRAY2RGB)

                # save registered image
                # if no directory is given save in same directory as moving image
                # otherwise save in specified directory
                registered_image_filename = f"{moving_image_stem}_registered_manual.tif"
                if self.resampled_image_directory is None :
                    registered_image_filepath = join(moving_image_dir, registered_image_filename)
                else :
                    registered_image_filepath = join(self.resampled_image_directory, registered_image_filename)
                cv2.imwrite(registered_image_filepath, resampled_img)

            if self.create_masks:

                # get directories and target image filename
                target_image_dir = row[1][0]
                moving_image_dir = row[1][1]
                target_image_filename = row[1][2]

                # read in target and moving images
                moving_img = standard_image_read(join(moving_image_dir, moving_image_filename))
                target_img = standard_image_read(join(target_image_dir, target_image_filename))

                # create mask of moving image
                # ones to match moving image size
                # resample moving image according to transformation, to size of target image
                target_size = target_img.shape
                mask_img = np.ones_like(moving_img)
                resampled_mask_img = cv2.warpAffine(mask_img, transformation_matrix, target_size)

                print (target_image_filename)

                # Convert grayscale to RGB so macOS Preview shows it properly
                resampled_mask_img = np.clip(resampled_mask_img * 255, 0, 255).astype(np.uint8)
                resampled_mask_img = cv2.cvtColor(resampled_mask_img, cv2.COLOR_GRAY2RGB)

                # save registered mask
                # if no directory is given save in same directory as moving image
                # otherwise save in specified directory
                registered_mask_image_filename = f"{moving_image_stem}_registered_mask_manual.tif"
                if self.resampled_image_directory is None:
                    registered_mask_image_filepath = join(moving_image_dir, registered_mask_image_filename)
                else:
                    registered_mask_image_filepath = join(self.mask_directory, registered_mask_image_filename)
                cv2.imwrite(registered_mask_image_filepath, resampled_mask_img)

        # add new outputs to alignments DF
        self.alignments['transformation_matrix_filenames'] = transformation_matrix_filenames

        # save as alignments as both .csv (for readability) and pickle (for programming convenience)
        self.alignments.to_csv(os.path.join(self.base_dir, self.upload_name + '_manual_registration_points.csv'))
        self.alignments.to_pickle(os.path.join(self.base_dir, self.upload_name + '_manual_registration_points.pkl'))

        # end program
        time.sleep(1)
        self.close()

    def set_original_target_image(self):

        # set image
        self.target_image.setPixmap(self.convert_ndarray_to_QPixmap(self.current_target_img_array))


    def set_original_moving_image(self):

        self.moving_image.setPixmap(self.convert_ndarray_to_QPixmap(self.current_moving_img_array))

    def set_point_on_moving_image(self, event):

        if self.current_n_points == 3:

            QtWidgets.QMessageBox.about(self, "points warning", "Cannot have more than 3 points in an image. Remove all points or select another image")

        else:

            # extract coordinate
            x = event.pos().x()
            y = event.pos().y()
            self.current_moving_image_point = (x, y)

            # draw point on image
            # set colour based on whether this is first, second or third point
            colour = self.get_colour(self.current_n_points)
            new_moving_image = self.current_moving_image
            new_moving_image = cv2.resize(new_moving_image, (self.image_size[0], self.image_size[1]))
            new_moving_image = cv2.circle(new_moving_image, (x, y), 3, colour, -1)
            self.new_moving_image = new_moving_image
            self.moving_image.setPixmap(self.convert_ndarray_to_QPixmap(new_moving_image))

            # enable adding the points if both points are set
            if (self.current_moving_image_point is not None) and (self.current_target_image_point is not None):

                self.add_points_button.setDisabled(False)

    def set_point_on_target_image(self, event):

        if self.current_n_points == 3:

            QtWidgets.QMessageBox.about(self, "points warning", "Cannot have more than 3 points in an image. Remove all points or select another image")

        else:

            # extract coordinate
            x = event.pos().x()
            y = event.pos().y()
            self.current_target_image_point = (x, y)

            # draw point on image
            # set colour based on whether this is first, second or third point
            colour = self.get_colour(self.current_n_points)
            new_target_image = self.current_target_image
            new_target_image = cv2.resize(new_target_image, (self.image_size[0], self.image_size[1]))
            new_target_image = cv2.circle(new_target_image, (x, y), 3, colour, -1)
            self.new_target_image = new_target_image
            self.target_image.setPixmap(self.convert_ndarray_to_QPixmap(new_target_image))

            # enable adding the points if both points are set
            if (self.current_target_image_point is not None) and (self.current_moving_image_point is not None) :

                self.add_points_button.setDisabled(False)

    def get_colour(self, ind):

        colour = np.zeros(3, )
        colour[ind] = 255
        return tuple(colour)

    # see https://stackoverflow.com/questions/34232632/convert-python-opencv-image-numpy-array-to-pyqt-qpixmap-image
    def convert_ndarray_to_QPixmap(self, img):
        w, h, ch = img.shape
        # Convert resulting image to pixmap
        if img.ndim == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        qimg = QtGui.QImage(img.data, h, w, 3 * h, QtGui.QImage.Format_RGB888)
        qpixmap = QtGui.QPixmap(qimg)
        #qpixmap = qpixmap.scaled(self.image_size[0], self.image_size[1])
        qpixmap = qpixmap.scaled(self.image_display_size[0], self.image_display_size[1])
        return qpixmap

    def add_points(self):

        # add to points table
        self.point_table.setItem(
            self.current_n_points, 0, QtWidgets.QTableWidgetItem(str(self.current_target_image_point)))
        self.point_table.setItem(
            self.current_n_points, 1, QtWidgets.QTableWidgetItem(str(self.current_moving_image_point)))

        # add to points list
        self.current_points.append(
            (self.current_target_image_point, self.current_moving_image_point))
        self.current_target_image_point = None
        self.current_moving_image_point = None

        # increment number of added points
        self.current_n_points = self.current_n_points + 1

        # store images with added points
        self.current_target_image = self.new_target_image
        self.current_moving_image = self.new_moving_image

        # update buttons
        self.add_points_button.setDisabled(True)

        if self.current_n_points < 3:

            self.remove_points_button.setDisabled(False)

        if self.current_n_points == 3:

            self.save_points_button.setDisabled(False)

        # don't let user change alignment selection with unsaved points added
        self.widgetAlignmentSelection.setDisabled(True)

    def save_points(self):

        # enter points in self.alignment
        target_image_points = []
        moving_image_points = []
        for point_pair in self.current_points :

            target_image_points.append(point_pair[0])
            moving_image_points.append(point_pair[1])

        self.alignments.at[self.current_alignment_row_index, 'target image points'] = target_image_points
        self.alignments.at[self.current_alignment_row_index, 'moving image points'] = moving_image_points

        # also add scale factors
        self.alignments.at[self.current_alignment_row_index, 'target image scale factors'] = (self.current_target_image_y_scale_factor, self.current_target_image_x_scale_factor)
        self.alignments.at[self.current_alignment_row_index, 'moving image scale factors'] = (self.current_moving_image_y_scale_factor, self.current_moving_image_x_scale_factor)

        # turn off save button
        self.save_points_button.setDisabled(True)

        # points are saved, allow change of alignment
        self.widgetAlignmentSelection.setDisabled(False)

        # disable saving as points are already saved
        self.save_points_button.setDisabled(True)

        # update counter, enable writing of points to file
        self.n_alignments_done = self.n_alignments_done + 1
        print("n alignments done: ", self.n_alignments_done)
        print("n alignments: ", self.n_alignments)

        if self.n_alignments_done == self.n_alignments :

            self.write_points_button.setDisabled(False)

    def remove_points(self):

        # empty table
        self.point_table.clear()
        self.point_table.setHorizontalHeaderLabels(["target image point", "moving image point"])

        # if points were saved, decrement counter of points aligments done
        if not self.alignments.at[self.current_alignment_row_index, 'target image points'] is None:
            self.n_alignments_done = self.n_alignments_done - 1

        # remove points from images
        self.set_original_target_image()
        self.set_original_moving_image()

        # remove points from self.alignment
        self.alignments.at[self.current_alignment_row_index, 'target image points'] = None
        self.alignments.at[self.current_alignment_row_index, 'moving image points'] = None

        # and to be thorough the scale factors too
        self.alignments.at[self.current_alignment_row_index, 'target image scale factors'] = None
        self.alignments.at[self.current_alignment_row_index, 'moving image scale factors'] = None

        # reset points and counter
        self.current_n_points = 0
        self.current_points = []
        self.current_target_image_point = None
        self.current_moving_point = None

        # can't remove or save points if we don't have any
        self.remove_points_button.setDisabled(True)
        self.save_points_button.setDisabled(True)

        # points are removed, allow change alignment
        self.widgetAlignmentSelection.setDisabled(False)

        # if we have removed the last saved points, disable writing
        if self.n_alignments_done == 0:

            self.write_points_button.setDisabled(True)

        print ("points removed. n alignments done: ", self.n_alignments_done)

#    def closeEvent(self, event):
#        buttonReply = QtWidgets.QMessageBox.question(self, 'Save points', "Save points",
 #                                                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
#        if buttonReply == QtWidgets.QMessageBox.Yes:
#            self.savePoints()
#        else:
#            print('No clicked.')


#sys._excepthook = sys.excepthook


#def exception_hook(exctype, value, traceback):
#    print(exctype, value, traceback)
#    sys._excepthook(exctype, value, traceback)
#    sys.exit(1)


#sys.excepthook = exception_hook


#app = QtWidgets.QApplication(sys.argv)

#sys.exit(app.exec_())

#window = MainWindow()

#window.show()
#app.exec_()

def call_app(base_dir, upload_name, manual_alignments_list, resample_images, resampled_image_dir, create_masks, mask_dir) :

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow(base_dir, upload_name, manual_alignments_list, resample_images, resampled_image_dir, create_masks, mask_dir)
    # window.set_alignments('foo')
    window.show()  # IMPORTANT!!!!! Windows are hidden by default.

    # Start the event loop.
    app.exec_()