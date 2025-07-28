#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
#from PyQt5.QtGui import *
#from PyAppSelectPoints_pyside import MainWindow
#from PyAppImgPainter_OCT_ANNO_SS_CNN_Test_use import MainWindow
# Only needed for access to command line arguments
import sys
import pickle
from PyAppSelectPoints_pyside import call_app


# You need one (and only one) QApplication instance per application.
# Pass in sys.argv to allow command line arguments for your app.
# If you know you won't use command line arguments QApplication([]) works too.
# directory to write points and transformations to
registration_dir = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\transformation_files"
# stem for points filename
upload_name = "test"
# path to read list of registration files from
registration_files_list = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\manual_registration_files.csv"
# flag whether to resample images and directory to save resampled images to if so
resample_images = True
resampled_image_dir = "C:\\Users\\Johnathan Young\\sandbox\\manual_registration_test\\resampled_images"
#app = QApplication(sys.argv)
#window = MainWindow(base_dir, upload_name, manual_alignments_list)
#window.set_alignments('foo')
#window.show()  # IMPORTANT!!!!! Windows are hidden by default.

# Start the event loop.
#app.exec_()

# Your application won't reach here until you exit and the event loop has stopped

call_app(registration_dir, upload_name, registration_files_list, resample_images=resample_images, resampled_image_dir=resampled_image_dir)
print('done!')

