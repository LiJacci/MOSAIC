"""Score paired point clouds using geometry, color and six UHM saliency maps."""

import argparse
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.special import expit
from skimage.metrics import structural_similarity
from tqdm import tqdm

from feature_extract import convert_color, get_feature_vector_data_scale, load_point_cloud


def read_saliency(path):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f'Missing or unreadable saliency map: {path}')
    return image


def compute_saliency_ssim_parallel(ref_sal_imgs, test_sal_dir):
    """Average SSIM over the six matching views, preserving their order."""
    def worker(i):
        path = test_sal_dir / f'{test_sal_dir.name}_sMap_{i + 1}.png'
        image = read_saliency(path)
        if image.shape != ref_sal_imgs[i].shape:
            raise ValueError(f'Saliency image size mismatch: {path}')
        if min(image.shape) < 7:
            raise ValueError(f'Saliency image must be at least 7 x 7: {path}')
        return structural_similarity(ref_sal_imgs[i], image, data_range=255)

    with ThreadPoolExecutor(max_workers=6) as pool:
        return float(np.mean(list(pool.map(worker, range(6)))))


def softmax_fusion(model1, model2, alpha):
    """Original sigmoid-weighted fusion (not exponential softmax)."""
    w1, w2 = expit(alpha * model1), expit(alpha * model2)
    return (w1 * model1 + w2 * model2) / (w1 + w2 + 1e-8)


def score(args, key_pts, key_feats, dist_coord, dist_feats, ref_geo_features, ref_color_features):
    dist_geo, dist_color = get_feature_vector_data_scale(
        dist_coord, dist_feats, key_pts, args.Kg, args.Kp, args.Kc, args.c)
    key_color = convert_color(key_feats, args.c).T[..., None]
    dist_color = np.mean(np.asarray(dist_color) - key_color, axis=2)
    ref_color = np.mean(np.asarray(ref_color_features) - key_color, axis=2)
    dist_geo, ref_geo = np.asarray(dist_geo), np.asarray(ref_geo_features)

    constant = 0.001
    geo_similarity = (2 * dist_geo * ref_geo + constant) / (dist_geo**2 + ref_geo**2 + constant)
    color_similarity = (2 * dist_color * ref_color + constant) / (dist_color**2 + ref_color**2 + constant)
    ssim_geo = np.mean(geo_similarity, axis=1)
    ssim_col = np.mean(color_similarity, axis=1)
    quality = softmax_fusion(np.mean(ssim_geo), np.mean(ssim_col), args.alpha)
    return quality, ssim_col, ssim_geo


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--gt_rootdir', type=Path, default=Path('WPC2.0/reference'))
    parser.add_argument('--test_rootdir', type=Path, default=Path('WPC2.0/distortion'))
    parser.add_argument('--gt_sal_rootdir', type=Path, default=Path('wpc2.0_saliency/reference'))
    parser.add_argument('--test_sal_rootdir', type=Path, default=Path('wpc2.0_saliency/distortion'))
    parser.add_argument('--output_rootdir', type=Path, default=Path('Ours/WPC2.0'))
    parser.add_argument('--Kg', type=int, default=100)
    parser.add_argument('--Kp', type=int, default=10)
    parser.add_argument('--Kc', type=int, default=10)
    parser.add_argument('--c', choices=('RGB', 'YUV', 'LAB'), default='RGB')
    parser.add_argument('--alpha', type=float, default=1)
    args = parser.parse_args()
    if args.Kg < 2 or args.Kp < 1 or args.Kc < 1:
        parser.error('Kg must be >= 2; Kp and Kc must be >= 1')
    if not np.isfinite(args.alpha):
        parser.error('alpha must be finite')
    return args


def test(args):
    """Append scores to all_test.csv; paths are relative to the working directory.

    Expected layout:
      reference/<ref>.ply; distortion/<ref>/<dist>.ply
      saliency/reference/<ref>/<ref>_sMap_1..6.png
      saliency/distortion/<ref>/<dist>/<dist>_sMap_1..6.png
    """
    for name in ('gt_rootdir', 'test_rootdir', 'gt_sal_rootdir', 'test_sal_rootdir', 'output_rootdir'):
        setattr(args, name, Path(getattr(args, name)))
    gt_files = sorted(args.gt_rootdir.glob('*.ply'))
    if not gt_files:
        raise FileNotFoundError(f'No reference PLY files found in {args.gt_rootdir}')
    args.output_rootdir.mkdir(parents=True, exist_ok=True)
    output_csv = args.output_rootdir / 'all_test.csv'
    write_header = not output_csv.exists() or output_csv.stat().st_size == 0

    for gt in tqdm(gt_files, desc='Reference clouds'):
        filename = gt.stem
        test_files = sorted((args.test_rootdir / filename).glob('*.ply'))
        if not test_files:
            raise FileNotFoundError(f'No distorted PLY files found in {args.test_rootdir / filename}')
        ref_coord, ref_feats = load_point_cloud(gt)
        ref_geo, ref_color = get_feature_vector_data_scale(
            ref_coord, ref_feats, ref_coord, args.Kg, args.Kp, args.Kc, args.c)
        ref_sal_imgs = [read_saliency(args.gt_sal_rootdir / filename / f'{filename}_sMap_{i + 1}.png')
                        for i in range(6)]

        for distorted in tqdm(test_files, desc=filename, leave=False):
            dist_coord, dist_feats = load_point_cloud(distorted)
            start = time.perf_counter()
            quality, ssim_col, ssim_geo = score(
                args, ref_coord, ref_feats, dist_coord, dist_feats, ref_geo, ref_color)
            saliency = compute_saliency_ssim_parallel(
                ref_sal_imgs, args.test_sal_rootdir / filename / distorted.stem)
            final = softmax_fusion(quality, saliency, args.alpha)
            if not np.isfinite(final):
                raise ValueError(f'Non-finite quality score: {distorted}')
            results = {
                'filename': distorted.stem, 'Final Score': final,
                'col1': ssim_col[0], 'col2': ssim_col[1], 'col3': ssim_col[2],
                'geo1': ssim_geo[0], 'geo2': ssim_geo[1], 'geo3': ssim_geo[2],
                'sal': saliency, 'process_time': time.perf_counter() - start,
            }
            pd.DataFrame([results]).to_csv(output_csv, mode='a', header=write_header, index=False)
            write_header = False


if __name__ == '__main__':
    test(parse_args())
