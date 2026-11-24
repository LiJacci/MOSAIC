"""MOSAIC geometry and neighborhood-color features; RGB values use [0, 1]."""

import numpy as np
import pandas as pd
from pyntcloud import PyntCloud
from scipy.spatial import cKDTree
from skimage.color import rgb2lab
from sklearn.neighbors import NearestNeighbors


def load_point_cloud(filedir):
    """Read named XYZ and 8-bit RGB fields; use black for uncolored clouds."""
    points = PyntCloud.from_file(str(filedir)).points
    columns = {str(name).lower(): name for name in points.columns}
    if not all(axis in columns for axis in ('x', 'y', 'z')):
        raise ValueError(f'{filedir}: missing x/y/z coordinates')
    coord = points[[columns[axis] for axis in ('x', 'y', 'z')]].to_numpy(dtype=float)
    if len(coord) < 3 or not np.isfinite(coord).all():
        raise ValueError(f'{filedir}: expected at least 3 points with finite coordinates')

    rgb_columns = [columns.get(full, columns.get(short))
                   for full, short in [('red', 'r'), ('green', 'g'), ('blue', 'b')]]
    if all(name is None for name in rgb_columns):
        feats = np.zeros((len(coord), 3))
    elif any(name is None for name in rgb_columns):
        raise ValueError(f'{filedir}: incomplete RGB fields')
    else:
        feats = points[rgb_columns].to_numpy(dtype=float) / 255.0
    if not np.isfinite(feats).all() or np.any((feats < 0) | (feats > 1)):
        raise ValueError(f'{filedir}: RGB fields must contain values in [0, 255]')
    return coord, feats


def convert_color(feats, color_space='RGB'):
    """Convert normalized RGB (..., 3) to the requested color space."""
    if color_space == 'RGB':
        return feats
    if color_space == 'YUV':
        matrix = np.array([[0.299, 0.587, 0.114],
                           [-0.14713, -0.28886, 0.436],
                           [0.615, -0.51499, -0.10001]])
        return feats @ matrix.T
    if color_space == 'LAB':
        return rgb2lab(feats.reshape(-1, 1, 3)).reshape(feats.shape)
    raise ValueError(f'Unknown color space: {color_space}')


def get_feature_vector_data_scale(coord, feats, coord_k, Kg, Kp, Kc, c='RGB'):
    """Match anchors, then extract linearity, curvature, spacing and colors.

    Geometry is computed on matched anchors. Color neighbors come from the
    full cloud. The original spacing definition includes the query point.
    Undefined eigenvalue ratios for collapsed neighborhoods are set to zero.
    """
    if len(coord_k) < 3 or len(coord) == 0:
        raise ValueError('Feature extraction needs at least 3 anchors and a nonempty cloud')
    if Kg < 2 or Kp < 1 or Kc < 1:
        raise ValueError('Kg must be >= 2; Kp and Kc must be >= 1')
    tree = cKDTree(coord)
    _, idx = tree.query(coord_k, k=1)
    matched_coord = coord[idx]
    cloud = PyntCloud(pd.DataFrame(matched_coord, columns=['x', 'y', 'z']))
    k_geometry = min(len(matched_coord) - 1, Kg)
    neighbors = cloud.get_neighbors(k=k_geometry)
    eigenvalues = cloud.add_scalar_field('eigen_values', k_neighbors=neighbors)
    with np.errstate(divide='ignore', invalid='ignore'):
        linearity_field = cloud.add_scalar_field('linearity', ev=eigenvalues)
        curvature_field = cloud.add_scalar_field('curvature', ev=eigenvalues)
    linearity = np.nan_to_num(cloud.points[linearity_field].to_numpy(), nan=0, posinf=0, neginf=0)
    curvature = np.nan_to_num(cloud.points[curvature_field].to_numpy(), nan=0, posinf=0, neginf=0)

    k_spacing = min(len(matched_coord) - 1, Kp)
    nbrs = NearestNeighbors(n_neighbors=k_spacing, algorithm='auto').fit(matched_coord)
    distances, _ = nbrs.kneighbors(matched_coord)
    spacing = np.mean(distances ** 2, axis=1)

    k_color = min(len(coord), Kc)
    _, color_indices = tree.query(matched_coord, k=k_color)
    color_indices = color_indices.reshape(len(matched_coord), k_color)
    colors = convert_color(feats[color_indices], c)
    return [linearity, curvature, spacing], [colors[..., channel] for channel in range(3)]
