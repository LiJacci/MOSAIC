function images = getProjection(pt)
%GETPROJECTION Render the six axis-aligned RR-CAP color projections.
% Adapted from weizhou-geek/RR-CAP (see LICENSE and README.md).
% Modified 2026-11-24: remove unused depth/occupancy calculations and eval;
% retain coordinate quantization, pixel placement, background and view order.
% Views: XY min/max Z, YZ min/max X, ZX min/max Y. No PCA is performed.

xyz = round(pt.Location);
rgb = single(pt.Color);
center = (max(xyz) + min(xyz)) / 2;
xyz = xyz - center;
scale = 150 / max(max(xyz));
xyz = round(xyz * scale) + 151;

data = [xyz + 1, rgb];
resolution = max(max(xyz)) + 1;
axisOrders = [1 2 3; 2 3 1; 3 1 2];
images = cell(6, 1);

for planeIdx = 1:3
    plane = data(:, [axisOrders(planeIdx, :), 4:6]);
    [sortedPlane, order] = sortrows(plane, 3);
    [firstIdx, lastIdx] = getIndex(sortedPlane(:, 1:2));
    surfaceIndices = {order(firstIdx), order(lastIdx)};

    for sideIdx = 1:2
        indices = surfaceIndices{sideIdx};
        pixels = sub2ind([resolution, resolution], ...
            plane(indices, 2), plane(indices, 1));
        rgbImage = ones(resolution, resolution, 3);
        for channel = 1:3
            channelImage = ones(resolution);
            channelImage(pixels) = plane(indices, channel + 3);
            rgbImage(:, :, channel) = channelImage;
        end
        images{2 * planeIdx - 2 + sideIdx} = rgbImage;
    end
end
end
