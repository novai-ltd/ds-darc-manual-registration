import SimpleITK as sitk
import numpy as np

def homogeneous_to_sitk_affine(homogeneous_matrix, dimension=2):
    """
    Converts a homogeneous transformation matrix to a SimpleITK AffineTransform.

    Args:
        homogeneous_matrix (numpy.ndarray): A homogeneous transformation matrix.
        dimension (int): The dimension of the transformation (default is 2 for 2D).

    Returns:
        sitk.AffineTransform: The corresponding SimpleITK AffineTransform.
    """

    # Extract rotation/scale/shear matrix (upper-left 2x2 for 2D, 3x3 for 3D)
    rotation_matrix = homogeneous_matrix[:dimension, :dimension]

    # Extract translation vector (last column)
    translation_vector = homogeneous_matrix[:dimension, dimension]

    # Create an AffineTransform
    affine_transform = sitk.AffineTransform(dimension)

    # Set the rotation/scale/shear matrix
    affine_transform.SetMatrix(rotation_matrix.flatten().tolist())

    # Set the translation vector
    affine_transform.SetTranslation(translation_vector.tolist())

    return affine_transform