import time
from pathlib import Path
from os.path import join
import functools
import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import numpy as np
import cv2
import pandas as pd
import pydicom

def standard_image_read(image_file_path):

    """
    Read image into a standard format

    First attempt to read as standard image file (.tif, .png & cetera)
    If fail try to read as DICOM
    If still fail, show blank image

    Args:
        image_file_path (str): path to image file

    Returns:
        image (np.array): single channel 8-bit image
        image_read (bool): flag indicating whether image was successfully read
    """

    try :

        # try to read image as standard image file (.tif, .png & cetera)
        # if it is none, try to read as dicom
        image = cv2.imread(str(image_file_path))
        if image is None:
            image = pydicom.dcmread(str(image_file_path)).pixel_array

        # if 3 channel, check if it is RGB or triple grayscale
        if image.ndim == 3:
            # image is triple grayscale if all channels are equal
            if np.all(image[:,:,0] == image[:,:,1]) and np.all(image[:,:,0] == image[:,:,2]):
                image = image[:,:,0]
            # image is RGB
            else:
                image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        # convert to uint8 if necessary
        if image.dtype == 'float64':
            image = (image * 255).astype('uint8')

        image_read = True

    # produce blank image with stamp if image cannot be read as either tif/png or DICOM
    except:
        # blank image
        image = np.zeros((1536, 1536), dtype='uint8')

        # text parameters
        origin = (150, 800)
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontScale = 5
        color = 255
        thickness = 10

        # write text on blank image
        image = cv2.putText(image, 'image not read', origin, font, fontScale, color, thickness, cv2.LINE_AA)
        image_read = False

    # return image and flag indicating whether image was successfully read
    return image, image_read

def standardise_normalise_image(image_array):
    """
    Normalize images intensities to 0-255 range
    Format original and normalised images uint8 image

    Args:
        image_array: numpy array of image intensities
    """
    min_pixel_value = image_array.min()
    max_pixel_value = image_array.max()
    normalized_image_array = (image_array - min_pixel_value) / (max_pixel_value - min_pixel_value)
    normalized_image_array *= 255.0 / normalized_image_array.max()
    normalized_image_array = normalized_image_array.astype("uint8")

    # convert image array to RGB uint8 if necessary
    if image_array.ndim == 2:
        image_array = np.dstack((image_array, image_array, image_array))
    elif image_array.ndim == 3:
        image_array = image_array

    # convert normalized image array to RGB uint8 if necessary
    if normalized_image_array.ndim == 2:
        normalized_image_array = np.dstack(
            (normalized_image_array, normalized_image_array, normalized_image_array))
    elif normalized_image_array.ndim == 3:
        normalized_image_array = normalized_image_array

    return image_array, normalized_image_array

class QResizingPixmapLabel(QLabel):
    """
    Class extending QLabel to allow for resizing of the image while keeping the aspect ratio

    On resize, set new image size, widget size, and scale factor as attributes of the main window
    and redraw both images

    Attributes:
        main_window (MainWindow): main window of the application
    """

    def __init__(self, main_window, moving_image):
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

            # calculate the new size of the image
            scaled = self._pixmap.scaled(self.width(), self.height(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            image_height = scaled.height()
            image_width = scaled.width()

            # redraw both images
            self.main_window.draw_image(True)
            self.main_window.draw_image(False)

            # reset the image and image widget size as attributes of the main window
            # and recalculate and store scale factors - can be different for each image if they have different original sizes
            self.main_window.image_display_size = (image_height, image_width)
            self.main_window.image_widget_size = (self.width(), self.height())
            self.main_window.moving_image_scale_factor = self.main_window.current_moving_image_array_size[0] / self.main_window.image_display_size[0]
            self.main_window.target_image_scale_factor = self.main_window.current_target_image_array_size[0] / self.main_window.image_display_size[0]

            # set alignment of the image in the widget to center
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)

class MainWindow(QtWidgets.QMainWindow):


    def __init__(self, registration_dir, upload_name, registration_files_csv, resample_images=True, resampled_image_directory=None, create_masks=False, mask_directory=None):

        """
        Initialize the main window of the application.

        Args:
            registration_dir (str): string representing root directory of outputs to write registration details to
            upload_name (str): string representing name of the upload to be registered, forming stem of files containing registration details
            resample_images (bool, optional): flag to indicate whether to resample images. Defaults to True.
            resampled_image_directory (str, optional): string representing directory to write resampled images to. Defaults to None.
            create_masks (bool, optional): flag to indicate whether to create binary masks of the aligned images. Defaults to False.
            mask_directory (str, optional): string representing directory to write binary masks to. Defaults to None.
        """
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

    def widget_to_image_coordinates(self, x_widget, y_widget):

        """
        Converts mouse position on widget to mouse position on image by calculating the margin
        surrounding the image and subtracting it from the mouse position

        Args:
            x_widget, y_widget (int): x and y position in widget coordinates

        Returns:
            x_image, y_image (int): x and y position in image coordinates
        """

        # get sizes of widget and pixmap and use them to calculate margins
        widget_width, widget_height = self.image_widget_size
        pixmap_width, pixmap_height = self.image_display_size
        left_margin = int((widget_width - pixmap_width) / 2)
        top_margin = int((widget_height - pixmap_height) / 2)

        # calculate image position of mouse pointer as mouse position minus margin
        x_image = x_widget - left_margin
        y_image = y_widget - top_margin

        return x_image, y_image

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

        """
        Set up the QResizingPixmapLabels to display the target and moving images. Set their initial size and
        link the mouse click events to the function to place a point.
        """

        # set initial image size
        self.image_display_size = (1250, 1250)

        # create grey QPixmap to initially show before an alignment has been selected
        grey = QtGui.QPixmap(self.image_display_size[0], self.image_display_size[1])
        grey.fill(QtGui.QColor('darkGray'))

        # create QLabels/QResizingPixmapLabels for target and moving images
        self.target_image = QResizingPixmapLabel(self, False)
        self.moving_image = QResizingPixmapLabel(self, True)

        # set the images to grey
        self.target_image.setPixmap(grey)
        self.moving_image.setPixmap(grey)

        # add one as scrollable area
        #self.scrollAreaTarget = QtWidgets.QScrollArea()
        #self.scrollAreaTarget.setWidget(self.target_image)
        #self.scrollAreaTarget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        #self.scrollAreaTarget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        #self.scrollAreaTarget.setWidgetResizable(True)

        # link mouse click on each image to function to place a point
        # use functools.partial to pass an extra argument to the function so it knows which image was clicked
        #self.target_image.mousePressEvent = functools.partial(self.set_point_on_image, False)
        #self.moving_image.mousePressEvent = functools.partial(self.set_point_on_image, True)

        # send mouse press events to filter so we can decide what to do based on whether they are left or right clicks
        self.target_image.mousePressEvent = functools.partial(self.mousePressLRFilter, False)
        self.moving_image.mousePressEvent = functools.partial(self.mousePressLRFilter, True)

        # also filter mouse release events
        self.target_image.mouseReleaseEvent = functools.partial(self.mouseReleaseFilter, False)
        self.moving_image.mouseReleaseEvent = functools.partial(self.mouseReleaseFilter, True)

        # switch off mouse tracking for both images intially
        # and link to tracking processing function
        self.target_image.setMouseTracking(False)
        self.target_image.mouseMoveEvent = functools.partial(self.process_mouse_move_on_image, False)
        self.moving_image.setMouseTracking(False)
        self.moving_image.mouseMoveEvent = functools.partial(self.process_mouse_move_on_image, True)

        # set minimum size for zooming in on
        self.minimum_zoomed_image_size = 32

    def mousePressLRFilter(self, is_moving_image, event):
        """
        A filter to decide what to do based on whether the mouse click was a left or right click

        If left click, call the function to set a point on the image
        If right, set up for click and drag (panning)

        Args:
            is_moving_image (bool): flag indicating whether the image clicked is the moving image (True) or target image (False)
            event (QMouseEvent): mouse event

        """
        if event.button() == Qt.LeftButton:
            self.set_point_on_image(is_moving_image, event)
        elif event.button() == Qt.RightButton:

            # extract coordinates of mouse click relative to widget
            x_widget = event.pos().x()
            y_widget = event.pos().y()

            # set click and drag positioning on the relevant image in IMAGE DISPLAY coordinates
            x_image_display, y_image_display = self.widget_to_image_coordinates(x_widget, y_widget)
            if is_moving_image:
                self.moving_image.setMouseTracking(True)
                self.moving_image_start_x = x_image_display
                self.moving_image_start_y = y_image_display

            else:
                self.target_image.setMouseTracking(True)
                self.target_image_start_x = x_image_display
                self.target_image_start_y = y_image_display

            if is_moving_image:
                image_str = "moving image"

            else:
                image_str = "target image"

            print(f"Right button press detected on {image_str} at x:{str(x_widget)}, y:{str(y_widget)} - no action assigned yet.")

    def mouseReleaseFilter(self, is_moving_image, event):
        if event.button() == Qt.RightButton:

            # turn off mouse tracking for area selection
            if is_moving_image:
                self.moving_image.setMouseTracking(False)

            else:
                self.target_image.setMouseTracking(False)

            # extract coordinates of mouse click relative to widget
            x_widget = event.pos().x()
            y_widget = event.pos().y()

            # calculate square selection coordinates and redraw image with new coordinates
            x_image_display, y_image_display = self.widget_to_image_coordinates(x_widget, y_widget)

            # calculate coordinates of square to select and pass to draw function
            # use these to then calculate the x and y limits in image coordinates
            # then call the draw function with these limits to redraw the image
            square_selection_coordinates = self.calculate_square_coordinates(is_moving_image, x_image_display, y_image_display)

            # protect against too much zooming in
            # if size of zoomed image is less than minimum, alert user with popup and do not update image except to remove selection box
            if is_moving_image:
                scale_factor = self.moving_image_scale_factor
            else:
                scale_factor = self.target_image_scale_factor
            zoomed_image_size = (square_selection_coordinates["x_max"] - square_selection_coordinates["x_min"]) * scale_factor
            if zoomed_image_size < self.minimum_zoomed_image_size:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Warning)
                msg.setText("Zoom limit reached")
                msg.setInformativeText(f"Cannot zoom in further. Minimum zoomed image size is {self.minimum_zoomed_image_size} pixels.")
                msg.setWindowTitle("Zoom limit")
                msg.exec_()
                square_selection_coordinates = None
                self.draw_image(is_moving_image, square_selection_coordinates)

            # if zoomed image size is ok, update image
            else:
                self.update_image_scale_parameters(is_moving_image, square_selection_coordinates)
                self.draw_image(is_moving_image)


    def process_mouse_move_on_image(self, is_moving_image, event):

        # decide which image is being moved over
        if is_moving_image:

            # process moving image mouse move if tracking on
            if self.moving_image.hasMouseTracking():

                # convert from widget coordinates to image display coordinates
                x_widget = event.pos().x()
                y_widget = event.pos().y()
                x_image_display, y_image_display = self.widget_to_image_coordinates(x_widget, y_widget)

                # calculate coordinates of square to select and pass to draw function
                square_selection_coordinates = self.calculate_square_coordinates(is_moving_image, x_image_display, y_image_display)
                self.square_selection_coordinates_moving = square_selection_coordinates
                self.draw_image(is_moving_image, square_selection_coordinates)
        else:

            # process target image mouse move if tracking on
            if self.target_image.hasMouseTracking():
                # convert from widget coordinates to image display coordinates
                x_widget = event.pos().x()
                y_widget = event.pos().y()
                x_image_display, y_image_display = self.widget_to_image_coordinates(x_widget, y_widget)

                # calculate coordinates of square to select and pass to draw function
                square_selection_coordinates = self.calculate_square_coordinates(is_moving_image, x_image_display,y_image_display)
                self.square_selection_coordinates_moving = square_selection_coordinates
                self.draw_image(is_moving_image, square_selection_coordinates)

    def calculate_square_coordinates(self, is_moving_image, x_current, y_current):

        """
        Take the current mouse position in image display coordinates. Calculate the square coordinates for selection from this,
        where the square has side length that is the minimum of the height and the width a rectangle defined by the current mouse position
        and starting mouse position that fits within the image boundaries.

        Args:
            is_moving_image (bool): flag indicating whether the image being processed is the moving image (True) or target image (False)
            x_current (int): x coordinate of mouse pointer in image display coordinates
            y_current (int): y coordinate of mouse pointer in image display coordinates

        Returns:
            x_min (int): minimum x coordinate of square in image display coordinates
            x_max (int): maximum x coordinate of square in image display coordinates
            y_min (int): minimum y coordinate of square in image display coordinates
            y_max (int): maximum y coordinate of square in image display coordinates

        """
        # get the starting mouse position
        if is_moving_image:
            x_start = self.moving_image_start_x
            y_start = self.moving_image_start_y
            image_width = self.moving_image.pixmap().width()
            image_height = self.moving_image.pixmap().height()
        else:
            x_start = self.target_image_start_x
            y_start = self.target_image_start_y
            image_width = self.target_image.pixmap().width()
            image_height = self.target_image.pixmap().height()

        # protect edges of image display: current mouse position can go outside image boundaries but square selection cannot
        # starting mouse position must be inside image boundaries already as set by mousePressEvent
        x_current = max(0, x_current)
        x_current = min(x_current, image_width-1)
        y_current = max(0, y_current)
        y_current = min(y_current, image_height-1)

        # sort out start and end coordinates to draw rectangle
        # find differences in x and y between current and start positions
        # scale the maxmimum difference to the same absolute value as the minimum difference to make a square
        # TODO feel there is a more elegant way to do this calculation
        x_diff = x_current - x_start
        y_diff = y_current - y_start
        if np.abs(x_diff) > np.abs(y_diff):
            x_current = x_start + np.sign(x_diff)*np.abs(y_diff)
        else:
            y_current = y_start + np.sign(y_diff)*np.abs(x_diff)

        # calculate min and max x and y coordinates of square
        x_max = max(x_current, x_start)
        x_min = min(x_current, x_start)
        y_max = max(y_current, y_start)
        y_min = min(y_current, y_start)

        # return square coordinates as a dictionary
        return {"x_min":x_min, "x_max":x_max, "y_min":y_min, "y_max":y_max}

    def update_image_scale_parameters(self, is_moving_image, square_selection_coordinates):

        """
        Takes a set of selected square coordinates in the current image display space. Uses the current x and y
        limits in the original image space, the scale factor and the square coordinates to update the x and y limits and scale factor

        Args:
            is_moving_image (bool): flag indicating whether the image being processed is the moving image (True) or target image (False)
            square_selection_coordinates (dict): dictionary containing the x and y min and max coordinates of the selected square in image display coordinates

        """

        # get the scale factor for the relevant image
        if is_moving_image:
            scale_factor = self.moving_image_scale_factor
            display_size = self.moving_image.pixmap().width()
        else:
            scale_factor = self.target_image_scale_factor
            display_size = self.target_image.pixmap().width()

        # get the selected square coordinates in image display space
        x_min_display = square_selection_coordinates["x_min"]
        x_max_display = square_selection_coordinates["x_max"]
        y_min_display = square_selection_coordinates["y_min"]
        y_max_display = square_selection_coordinates["y_max"]

        # get the current x and y limits in original image space
        if is_moving_image:
            x_min_original = self.current_moving_image_x_min
            x_max_original = self.current_moving_image_x_max
            y_min_original = self.current_moving_image_y_min
            y_max_original = self.current_moving_image_y_max
        else:
            x_min_original = self.current_target_image_x_min
            x_max_original = self.current_target_image_x_max
            y_min_original = self.current_target_image_y_min
            y_max_original = self.current_target_image_y_max

        # self.moving_image_scale_factor = self.current_moving_image_array_size[1] / self.moving_image.width()

        # new limits in original image space are old limits plus the selected square coordinates multiplied by scale factor
        x_min_original_updated = int(x_min_original + (x_min_display*scale_factor))
        x_max_original_updated = int(x_min_original + (x_max_display*scale_factor))
        y_min_original_updated = int(y_min_original + (y_min_display*scale_factor))
        y_max_original_updated = int(y_min_original + (y_max_display*scale_factor))

        # calculate new scale factor
        scale_factor_updated = (x_max_original_updated - x_min_original_updated) / display_size

        # save the updated limits and scale factor
        if is_moving_image:
            self.current_moving_image_x_min = x_min_original_updated
            self.current_moving_image_x_max = x_max_original_updated
            self.current_moving_image_y_min = y_min_original_updated
            self.current_moving_image_y_max = y_max_original_updated
            self.moving_image_scale_factor = scale_factor_updated
        else:
            self.current_target_image_x_min = x_min_original_updated
            self.current_target_image_x_max = x_max_original_updated
            self.current_target_image_y_min = y_min_original_updated
            self.current_target_image_y_max = y_max_original_updated
            self.target_image_scale_factor = scale_factor_updated

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
                     'target image points', 'moving image points'])
        self.alignments[['target image points', 'moving image points']] = self.alignments[
            ['target image points', 'moving image points']].astype('object')
        self.alignments[['target image points', 'moving image points']] = self.alignments[
            ['target image points', 'moving image points']] = None
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
        self.layoutPointWidget = QWidget()
        self.layoutPointWidget.setLayout(self.layoutPointControl)
        self.layoutPointWidget.setFixedWidth(250)

        # set up overall layout with qgrid
        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.target_image_label, 0, 0)
        self.layout.addWidget(self.moving_image_label, 0, 1)
        self.layout.addWidget(self.point_table_label, 0, 2)
        self.layout.addWidget(self.target_image, 1, 0)
        #self.layout.addWidget(self.scrollAreaTarget, 1, 0)
        self.layout.addWidget(self.moving_image, 1, 1)
        self.layout.addWidget(self.layoutPointWidget, 1, 2)
        self.layout.addWidget(self.image_selection_label, 2, 0, 1, 2)
        self.layout.addWidget(self.widgetAlignmentSelection, 3, 0, 1, 2)

        # set overall layout as central widget
        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(self.layout)
        self.setCentralWidget(self.widget)

    def connect_button_functionality(self):

        """
        Set up functionality of controls in main layout by connecting buttons to functions
        and setting initial states of buttons
        """

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

        """
        Load the selected alignment/pair of eyes
        Clear the point table and load any previously saved points for this alignment
        Set current moving and target image files and current alignment row in alignments table, and display the images
        Save image sizes and scale factors for later use

        Args:
            alignment_str: string with the format 'target_image_file_to_moving_image_file' that identifies the alignment to be loaded
        """

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
        current_moving_img_array, self.current_moving_image_read = standard_image_read(join(self.current_moving_image_dir, self.current_moving_image_file))
        current_target_img_array, self.current_target_image_read = standard_image_read(join(self.current_target_image_dir, self.current_target_image_file))

        # standarise image format and normalise contents
        self.current_moving_img_array, self.current_moving_img_array_norm = standardise_normalise_image(current_moving_img_array)
        self.current_target_img_array, self.current_target_img_array_norm = standardise_normalise_image(current_target_img_array)

        # store real image sizes so we can calculate scale factors after any resizing
        self.current_moving_image_array_size = self.current_moving_img_array.shape[:2]
        self.current_target_image_array_size = self.current_target_img_array.shape[:2]

        # calculate scale factors now
        self.moving_image_scale_factor = self.current_moving_image_array_size[1] / self.moving_image.width()
        self.target_image_scale_factor = self.current_target_image_array_size[1] / self.target_image.width()

        # set x and y display limits in original image space
        self.current_moving_image_x_min = 0
        self.current_moving_image_x_max = self.current_moving_image_array_size[1]
        self.current_moving_image_y_min = 0
        self.current_moving_image_y_max = self.current_moving_image_array_size[0]
        self.current_target_image_x_min = 0
        self.current_target_image_x_max = self.current_target_image_array_size[1]
        self.current_target_image_y_min = 0
        self.current_target_image_y_max = self.current_target_image_array_size[0]

        # set images
        self.set_original_target_image()
        self.set_original_moving_image()

        # draw points if necessary
        # and repopulate table
        existing_target_image_points = self.alignments.at[self.current_alignment_row_index, 'target image points']
        if not existing_target_image_points == None :

            self.draw_image(True)
            self.draw_image(False)

            self.current_n_points = 3
            # turn off save button
            self.save_points_button.setDisabled(True)
            self.remove_points_button.setDisabled(False)

            # add to points table
            existing_moving_image_points = self.alignments.at[self.current_alignment_row_index, 'moving image points']
            for i, moving_image_point in enumerate(existing_moving_image_points):

                target_image_point = existing_target_image_points[i]
                self.point_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(target_image_point)))
                self.point_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(moving_image_point)))

        else:

            # enable addition of points
            self.remove_points_button.setDisabled(True)

            # initialise point storage
            # points added but not saved
            self.stashed_target_image_points = None
            self.stashed_moving_image_points = None

            # points being added
            self.current_moving_image_point = None
            self.current_target_image_point = None

            # set number of current points to 0
            self.current_n_points = 0

    def write_points_to_file(self):

        """
        Save all saved points to a csv file and a pkl file for later use
        Optionally resample the images and save the resampled images to a specified directory
        Optionally create masks for the resampled images and save to a specified directory
        """

        # only enable if all points have been completed
        if self.n_alignments_done < self.n_alignments :

            QtWidgets.QMessageBox.about(self, "points warning", "Cannot save to file before all required points have been saved")

        # initialize lists of extra outputs: transformation matrix text files
        transformation_matrix_filenames = []

        # iterate through alignments generating a transformation matrix txt file and a sitk transformation object for each one
        for row in self.alignments.iterrows() :

            # extract target and moving points
            # no longer need to save scale factors as image display sizes vary anyway.
            # points are saved in original image pixel space
            moving_image_filename = row[1][3]
            target_points = row[1][4]
            moving_points = row[1][5]

            # convert points to numpy arrays, allowing for scale
            target_points = np.array(target_points)
            moving_points = np.array(moving_points)

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
                moving_img, moving_img_read = standard_image_read(join(moving_image_dir, moving_image_filename))
                target_img, target_img_read = standard_image_read(join(target_image_dir, target_image_filename))

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

            # if option is selected, create mask for resampled image and save
            if self.create_masks:

                # get directories and target image filename
                target_image_dir = row[1][0]
                moving_image_dir = row[1][1]
                target_image_filename = row[1][2]

                # read in target and moving images
                moving_img, moving_img_read = standard_image_read(join(moving_image_dir, moving_image_filename))
                target_img, target_img_read = standard_image_read(join(target_image_dir, target_image_filename))

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

        """
        Set the original target image (no point markers) in the target image display widget.
        """

        # set image
        self.target_image.setPixmap(self.convert_ndarray_to_QPixmap(self.current_target_img_array))

    def set_original_moving_image(self):

        """
        Set the original moving image (no point markers) in the moving image display widget.
        """

        self.moving_image.setPixmap(self.convert_ndarray_to_QPixmap(self.current_moving_img_array))

    def set_point_on_image(self, moving_image, event):

        """
        Process a mouse click event on either the moving or target image display widget to set a point.
        """

        # check if already 3 points - if so display warning and do not add point
        if self.current_n_points == 3:

            QtWidgets.QMessageBox.about(self, "points warning", "Cannot have more than 3 points in an image. Remove all points or select another image")

        # if we have less than 3 points, add point
        else:

            # extract coordinates of mouse click relative to widget
            x_widget = event.pos().x()
            y_widget = event.pos().y()

            # then convert widget coords to coordinates relative to image as displayed in app
            x_image_display, y_image_display = self.widget_to_image_coordinates(x_widget, y_widget)

            # get correct scale factor and offsets for whichever image is being processed
            if moving_image :
                scale_factor = self.moving_image_scale_factor
                x_min_original = self.current_moving_image_x_min
                y_min_original = self.current_moving_image_y_min
            else:
                scale_factor = self.target_image_scale_factor
                x_min_original = self.current_target_image_x_min
                y_min_original = self.current_target_image_y_min

            # convert displayed image coordinates to original image coordinates
            x_image_original = int(x_image_display * scale_factor) + x_min_original
            y_image_original = int(y_image_display * scale_factor) + y_min_original

            # choose which image to further process
            if moving_image :

                # store the current coordinate
                # trigger redraw of image, including newly added point
                # enable adding the points if both points are set
                self.current_moving_image_point = np.array([x_image_original, y_image_original])
                self.draw_image(True)
                if (self.current_moving_image_point is not None) and (self.current_target_image_point is not None):
                    self.add_points_button.setDisabled(False)

            else :

                # store the current coordinate
                # trigger redraw of image, including newly added point
                # enable adding the points if both points are set
                self.current_target_image_point = np.array([x_image_original, y_image_original])
                self.draw_image(False)
                if (self.current_moving_image_point is not None) and (self.current_target_image_point is not None):
                    self.add_points_button.setDisabled(False)

    def draw_image(self, moving_image, square_selection_coordinates=None):

        """
        Draw either the moving or target image in the relevant display widget, drawing either the saved point pairs
        or the stashed points and/or the current point if set.
        """

        # choose which image to process
        if moving_image:

            # get the relevant original space image limits and scale factor
            x_min = self.current_moving_image_x_min
            x_max = self.current_moving_image_x_max
            y_min = self.current_moving_image_y_min
            y_max = self.current_moving_image_y_max

            # crop the display image to the min and max limits
            cropped_image_array = self.current_moving_img_array_norm[y_min:y_max, x_min:x_max, :].copy()

            # reset background to remove any previous point marking and get canvas to (re)draw points on using PyQt
            #self.moving_image.setPixmap(self.convert_ndarray_to_QPixmap(self.current_moving_img_array_norm))
            self.moving_image.setPixmap(self.convert_ndarray_to_QPixmap(cropped_image_array))
            canvas = self.moving_image.pixmap()
            image = self.moving_image

            # get points as list of tuples
            # either from existing points in alignment DF or from stashed points/current point if not
            saved_image_points = self.alignments.at[self.current_alignment_row_index, 'moving image points']
            if saved_image_points is None:
                existing_image_points = self.stashed_moving_image_points
                current_image_point = self.current_moving_image_point

        else :

            # get the relevant original space image limits and scale factor
            x_min = self.current_target_image_x_min
            x_max = self.current_target_image_x_max
            y_min = self.current_target_image_y_min
            y_max = self.current_target_image_y_max

            # crop the display image to the min and max limits
            cropped_image_array = self.current_target_img_array_norm[y_min:y_max, x_min:x_max, :].copy()

            # reset background to remove any previous point marking and get canvas to (re)draw points on using PyQt
            #self.target_image.setPixmap(self.convert_ndarray_to_QPixmap(self.current_target_img_array_norm))
            self.target_image.setPixmap(self.convert_ndarray_to_QPixmap(cropped_image_array))
            canvas = self.target_image.pixmap()
            image = self.target_image

            # get points as list of tuples
            # either from existing points in alignment DF or from stashed points/current point if not
            saved_image_points = self.alignments.at[self.current_alignment_row_index, 'target image points']
            if saved_image_points is None:
                existing_image_points = self.stashed_target_image_points
                current_image_point = self.current_target_image_point

        # either set saved image points as image points to draw, or use stashed/current points if no saved points
        if saved_image_points is not None:
            image_points = saved_image_points
        else:
            # combine existing and current points into single list so we can draw all of them - either or both may be None
            # TODO find a more elegant way of doing this if possible?
            if existing_image_points is None and current_image_point is None:
                image_points = []
            elif existing_image_points is None and current_image_point is not None:
                image_points = [current_image_point]
            elif existing_image_points is not None and current_image_point is None:
                image_points = existing_image_points
            else:
                image_points = existing_image_points + [current_image_point]

        # Create a QPainter object and set the brush color and size
        painter = QPainter(canvas)

        # loop through current points and draw them with the correct colour
        for ind, point in enumerate(image_points):

            # extract point coordinates, convert them to display image coordinates with the appropriate scale factor
            # check if point lies within the currently displayed area
            # use index to set colour, and draw a circle at that point
            if moving_image:
                scale_factor = self.moving_image_scale_factor
                x_min_original = self.current_moving_image_x_min
                x_max_original = self.current_moving_image_x_max
                y_min_original = self.current_moving_image_y_min
                y_max_original = self.current_moving_image_y_max

            else:
                scale_factor = self.target_image_scale_factor
                x_min_original = self.current_target_image_x_min
                x_max_original = self.current_target_image_x_max
                y_min_original = self.current_target_image_y_min
                y_max_original = self.current_target_image_y_max

            # skip if point lies outside currently displayed area
            x_image_original, y_image_original = point
            if (point[0] < x_min_original) or (point[0] > x_max_original) or (point[1] < y_min_original) or (point[1] > y_max_original):
                continue

            # if point lies within currently displayed area, convert to display coordinates and draw
            x_image_display = int((x_image_original - x_min_original) / scale_factor)
            y_image_display = int((y_image_original - y_min_original) / scale_factor)
            colour = self.get_colour(ind)

            painter.setPen(QPen(colour, 1, Qt.SolidLine))
            painter.setBrush(QBrush(colour, Qt.SolidPattern))
            painter.drawEllipse(x_image_display-4, y_image_display-4, 8, 8)

        # finally draw an outline of the selected area if we are given current_selection_end_xy
        if square_selection_coordinates is not None:

            if moving_image:
                print(f"start xy: {int(self.moving_image_start_x)}, {int(self.moving_image_start_y)}")
            else:
                print(f"start xy: {int(self.target_image_start_x)}, {int(self.target_image_start_y)}")

            # extract coordinates from dictionary and get height and width
            x_min = square_selection_coordinates["x_min"]
            x_max = square_selection_coordinates["x_max"]
            y_min = square_selection_coordinates["y_min"]
            y_max = square_selection_coordinates["y_max"]
            width = x_max - x_min
            height = y_max - y_min

            # use top left corner, width and height to draw rectangle
            # set pen to dashed line width 2 and no brush
            rectangle = QRectF(x_min, y_min, width, height)
            painter.setPen(QPen(Qt.yellow, 2, Qt.DashDotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rectangle)

        # Update the QLabel with the new pixmap and redraw
        image.setPixmap(canvas)
        image.repaint()
        painter.end()










    def get_colour(self, ind):

        """
        Take an index and return a colour for drawing the corresponding point pair.
        """

        colour_dict = {0: Qt.red, 1: Qt.cyan, 2: Qt.green}
        return colour_dict[ind]

    # see https://stackoverflow.com/questions/34232632/convert-python-opencv-image-numpy-array-to-pyqt-qpixmap-image
    def convert_ndarray_to_QPixmap(self, img):

        """
        Convert a numpy ndarray image to a QPixmap, scaling it to fit the display widget.

        Args:
            img: ndarray: RGB image as h x w x channels numpy array

        Returns:
            qpixmap: QPixmap: QPixmap version of input image, scaled to fit display widget
        """
        # image does not have to be RGB but must have 3rd dimension
        # get image dimensions
        w, h, ch = img.shape

        # Convert to RGB if needed
        if img.ndim == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        # Convert to QImage and then to QPixmap
        qimg = QtGui.QImage(img.data, h, w, 3 * h, QtGui.QImage.Format_RGB888)
        qpixmap = QtGui.QPixmap(qimg)
        qpixmap = qpixmap.scaled(self.image_display_size[0], self.image_display_size[1])
        return qpixmap

    def add_points(self):

        """
        Display the current point pair in the points table and stash them for later saving to the alignments DataFrame.
        """

        # add to points table
        self.point_table.setItem(
            self.current_n_points, 0, QtWidgets.QTableWidgetItem(str(self.current_target_image_point)))
        self.point_table.setItem(
            self.current_n_points, 1, QtWidgets.QTableWidgetItem(str(self.current_moving_image_point)))

        # move added points from current to stashed
        current_moving_image_point = self.current_moving_image_point
        current_target_image_point = self.current_target_image_point
        if self.stashed_moving_image_points is None:
            self.stashed_moving_image_points = [current_moving_image_point]
            self.stashed_target_image_points = [current_target_image_point]

        else:
            self.stashed_moving_image_points.append(current_moving_image_point)
            self.stashed_target_image_points.append(current_target_image_point)
        self.current_target_image_point = None
        self.current_moving_image_point = None

        # increment number of added points
        self.current_n_points = self.current_n_points + 1

        # update buttons
        self.add_points_button.setDisabled(True)
        if self.current_n_points < 3:
            self.remove_points_button.setDisabled(False)
        if self.current_n_points == 3:
            self.save_points_button.setDisabled(False)

        # don't let user change alignment selection with unsaved points added
        self.widgetAlignmentSelection.setDisabled(True)

    def save_points(self):

        """
        When all 3 point pairs have been added, save them to the alignments DataFrame.
        """

        # set stashed points to current alignment row in alignments DataFrame
        self.alignments.at[self.current_alignment_row_index, 'target image points'] = self.stashed_target_image_points
        self.alignments.at[self.current_alignment_row_index, 'moving image points'] = self.stashed_moving_image_points

        # turn off save button
        self.save_points_button.setDisabled(True)

        # points are saved, allow change to another alignment
        self.widgetAlignmentSelection.setDisabled(False)

        # disable saving as points are already saved
        self.save_points_button.setDisabled(True)

        # update counter, enable writing of points to file
        self.n_alignments_done = self.n_alignments_done + 1
        print("n alignments done: ", self.n_alignments_done)
        print("n alignments: ", self.n_alignments)

        # if we have saved points for all alignments, enable writing of points to file
        if self.n_alignments_done == self.n_alignments :

            self.write_points_button.setDisabled(False)

    def remove_points(self):

        """
        Remove the stashed or saved points for the current alignment.
        """

        # empty points table so points are not shown
        self.point_table.clear()
        self.point_table.setHorizontalHeaderLabels(["target image point", "moving image point"])

        # if points were saved, decrement counter of points aligments done
        if not self.alignments.at[self.current_alignment_row_index, 'target image points'] is None:
            self.n_alignments_done = self.n_alignments_done - 1

        # remove points from self.alignment
        self.alignments.at[self.current_alignment_row_index, 'target image points'] = None
        self.alignments.at[self.current_alignment_row_index, 'moving image points'] = None

        # remove points from images and redraw
        self.stashed_moving_image_points = None
        self.stashed_target_image_points = None
        self.current_moving_image_point = None
        self.current_target_image_point = None
        self.draw_image(True)
        self.draw_image(False)

        # reset counter
        self.current_n_points = 0

        # can't remove or save points if we don't have any
        self.remove_points_button.setDisabled(True)
        self.save_points_button.setDisabled(True)

        # points are removed, allow change alignment
        self.widgetAlignmentSelection.setDisabled(False)

        # if we have removed the last saved points, disable writing
        if self.n_alignments_done == 0:

            self.write_points_button.setDisabled(True)

        print ("points removed. n alignments done: ", self.n_alignments_done)

def call_app(base_dir, upload_name, manual_alignments_list, resample_images, resampled_image_dir, create_masks, mask_dir) :

    """
    Initialize and call the PyQt application with the correct arguments.

    Args:
        base_dir (str): string representing root directory of outputs to write registration details to
        upload_name (str): string representing name of the upload to be registered, forming stem of files containing registration details
        manual_alignments_list (str): string representing path to csv file containing list of manual alignments to perform
        resample_images (bool, optional): flag to indicate whether to resample images. Defaults to True.
        resampled_image_directory (str, optional): string representing directory to write resampled images to. Defaults to None.
        create_masks (bool, optional): flag to indicate whether to create binary masks of the aligned images. Defaults to False.
        mask_directory (str, optional): string representing directory to write binary masks to. Defaults to None.
    """

    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow(base_dir, upload_name, manual_alignments_list, resample_images, resampled_image_dir, create_masks, mask_dir)
    # window.set_alignments('foo')
    window.show()  # IMPORTANT!!!!! Windows are hidden by default.

    # Start the event loop.
    app.exec_()