# PLY 点云 → 六视图投影 → UHM 显著性图

本目录仅保留批处理流程及运行依赖：读取 PLY 点云，使用 RR-CAP 的六个轴向视图投影，逐图调用 UHM，保存灰度 PNG。没有质量评分或训练步骤。

## 运行

在 MATLAB 中打开 `matlab/ply_folder_to_uhm_saliency.m`，修改顶部配置后运行：

```matlab
inputRoot = 'WPC2.0';
outputRoot = 'wpc2.0_saliency';
useCenterBias = true;
saveProjectionImages = false;
overwriteExisting = true;
limit = 0;
```

输入、输出相对路径以 MATLAB 当前工作目录为基准；可改为绝对路径。依赖目录相对于入口脚本定位。`limit = 0` 处理全部 PLY，设为 `1` 可先运行一个文件。默认覆盖已有显著性图。

需要支持脚本局部函数的 MATLAB，以及提供以下函数的工具箱：

- `pcread`、`pointCloud`：点云读取和构造。
- `imresize`、`imfilter`、`fspecial` 等：图像处理。
- `pdist2`：UHM 特征距离计算。

## 实现与输出

1. 递归读取所有 `.ply` 文件；缺少颜色时赋白色。
2. 坐标取整，以包围盒中心居中，再统一缩放、量化。保留 RR-CAP 原有网格规则，非退化点云通常生成 **302 × 302** 投影，没有 PCA 旋转。
3. 按 XY 平面最小/最大 Z、YZ 平面最小/最大 X、ZX 平面最小/最大 Y 的顺序生成六张 RGB 图。每个可见点占一个像素，背景 RGB 为 `(1, 1, 1)`。
4. 对每张 RGB 图调用 UHM，默认启用中心偏置。归一化为 `[0, 1]` 后保存为 8 位灰度 PNG。

输入 `inputRoot/distortion/model/sample.ply` 对应：

```text
outputRoot/distortion/model/sample/
  sample_sMap_1.png
  ...
  sample_sMap_6.png
```

开启 `saveProjectionImages` 时，同时保存 `sample_proj_1.png` 至 `sample_proj_6.png`。关闭覆盖时，已有显著性图对应的视图会跳过，其投影图也不会补写。

保留原有异常处理：单个点云处理抛错时记录 warning，继续下一个点云；当前点云可能只写出部分视图。没有备用显著性算法。保存前的归一化会将非有限值置零，常数结果保存为全黑图。

## 目录

```text
matlab/ply_folder_to_uhm_saliency.m  批处理入口及文件辅助函数
repos/RR-CAP/getProjection.m        六视图 RGB 投影
repos/RR-CAP/getIndex.m             每像素最小/最大深度点选择
repos/UHM/computeSaliency.m         UHM 显著性入口
repos/UHM/src/                     UHM 推理依赖
repos/UHM/bases/                   当前两层 ISA 网络所需的两份权重
```

此次整理移除了 RR-CAP 评分示例、UHM 演示图片和脚本、未调用的 `sc-master` 可视化工具，以及当前网络未使用的 `gs_4` 权重。投影函数去除了无用的深度图、占据图和中间统计计算；保留原有 RGB 投影规则。UHM 推理源代码及两份使用中的权重保持不变。

## 来源

- RR-CAP：Wei Zhou 等，*Reduced-Reference Quality Assessment of Point Clouds via Content-Oriented Saliency Projection*，IEEE Signal Processing Letters，2023。这里只使用其投影实现。
- UHM：H. R. Tavakoli、J. Laaksonen，*Bottom-up Fixation Prediction Using Unsupervised Hierarchical Models*，ACCV 2016 Workshop on Assistive Vision。

第三方来源说明与许可证保留在各自的 `README.md` 和 `LICENSE` 中。
