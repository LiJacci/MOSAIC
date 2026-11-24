# MOSAIC

**Multimodal Perceptual Cue Fusion for Full-Reference Point Cloud Quality Assessment**

Jiaxin Li, Tong Chen, Zehong Li, Dandan Ding, and Zhan Ma

[Project page](https://njuvision.github.io/MOSAIC)

## Repository structure

```text
MOSAIC_Final_Code/
├── README.md
├── feature_extract.py                 # PLY loading and geometry/color features
├── quality_all.py                     # Batch scoring and CSV output
└── saliency_pipeline/
    ├── README_MATLAB.md               # Additional saliency-pipeline notes
    ├── matlab/
    │   └── ply_folder_to_uhm_saliency.m
    └── repos/
        ├── RR-CAP/                    # Six-view projection helpers and license
        └── UHM/                       # Saliency inference, basis files and license
```

## Requirements

### Python

Create an environment and install the scoring dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install numpy pandas scipy scikit-learn scikit-image pyntcloud opencv-python-headless tqdm
```

### MATLAB

The saliency preprocessing stage requires MATLAB with support for local functions in scripts and the following functionality:

- Point-cloud I/O: `pcread` and `pointCloud`.
- Image processing: `imresize`, `imfilter`, `fspecial`, and related functions.
- Pairwise distances: `pdist2`.

Ensure the relevant MATLAB toolboxes are installed. The UHM source and the two basis files needed by the configured network are included. Both stages use the CPU; a GPU is not required.

## Prepare the data

Organize the reference and distorted PLY files as follows:

```text
WPC2.0/
├── reference/
│   ├── object01.ply
│   └── object02.ply
└── distortion/
    ├── object01/
    │   ├── object01_dist01.ply
    │   └── object01_dist02.ply
    └── object02/
        └── object02_dist01.ply
```

## 1. Generate the saliency maps

Open [ply_folder_to_uhm_saliency.m](saliency_pipeline/matlab/ply_folder_to_uhm_saliency.m) in MATLAB. Edit the configuration **inside the script** before running it. Use absolute paths to avoid dependence on MATLAB's working directory:

```matlab
inputRoot = '/absolute/path/to/WPC2.0';
outputRoot = '/absolute/path/to/wpc2.0_saliency';
useCenterBias = true;
saveProjectionImages = false;
overwriteExisting = true;
limit = 0;
```

Set `inputRoot` to the dataset root containing both `reference` and `distortion`. Run the script to recursively process the PLY files.

- `limit = 0` processes all files; a positive value processes only the first N files for a preliminary check.
- `saveProjectionImages = true` also saves the RGB views.
- `overwriteExisting = false` skips existing saliency maps. RGB views for skipped maps are not regenerated.

The script uses RR-CAP's axis-aligned projection helpers and UHM saliency inference. Each cloud produces six grayscale PNG saliency maps:

```text
wpc2.0_saliency/
├── reference/
│   └── object01/
│       ├── object01_sMap_1.png
│       ├── ...
│       └── object01_sMap_6.png
└── distortion/
    └── object01/
        └── object01_dist01/
            ├── object01_dist01_sMap_1.png
            ├── ...
            └── object01_dist01_sMap_6.png
```

The six views are ordered as XY at minimum/maximum Z, YZ at minimum/maximum X, and ZX at minimum/maximum Y. Use the same preprocessing settings for reference and distorted clouds.

## 2. Compute quality scores

From the repository root, run:

```bash
python quality_all.py
```

| Option | Default | Description |
| --- | --- | --- |
| `--gt_rootdir` | `WPC2.0/reference` | Reference PLY directory |
| `--test_rootdir` | `WPC2.0/distortion` | Distorted PLY directories grouped by reference |
| `--gt_sal_rootdir` | `wpc2.0_saliency/reference` | Reference saliency root |
| `--test_sal_rootdir` | `wpc2.0_saliency/distortion` | Distorted saliency root |
| `--output_rootdir` | `Ours/WPC2.0` | Output directory |
| `--Kg` | `100` | Geometry neighborhood parameter; at least 2 |
| `--Kp` | `10` | Point-spacing neighborhood parameter; at least 1 |
| `--Kc` | `10` | Color neighborhood parameter; at least 1 |
| `--c` | `RGB` | Color space: `RGB`, `YUV`, or `LAB` |
| `--alpha` | `1` | Sigmoid weighting slope |

## Acknowledgments and licensing

The saliency preprocessing uses code from:

- **RR-CAP:** Wei Zhou, Guanghui Yue, Ruizeng Zhang, Yipeng Qin, and Hantao Liu, *Reduced-Reference Quality Assessment of Point Clouds via Content-Oriented Saliency Projection*, IEEE Signal Processing Letters, 2023. See the bundled [source acknowledgment](saliency_pipeline/repos/RR-CAP/README.md) and [license](saliency_pipeline/repos/RR-CAP/LICENSE).
- **UHM:** H. R. Tavakoli and J. Laaksonen, *Bottom-up Fixation Prediction Using Unsupervised Hierarchical Models*, ACCV 2016 Workshop on Assistive Vision. See the bundled [source acknowledgment](saliency_pipeline/repos/UHM/README.md) and [license notice](saliency_pipeline/repos/UHM/LICENSE).

No project-level license has been specified for the MOSAIC-specific code in this snapshot. The bundled third-party notices apply to their respective components; they do not establish a license for the entire repository.
