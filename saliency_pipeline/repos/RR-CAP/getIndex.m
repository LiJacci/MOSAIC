function [firstIdx, lastIdx] = getIndex(pixelCoordinates)
%GETINDEX Select the first/last point at each pixel in depth-sorted data.
% Adapted from weizhou-geek/RR-CAP (see LICENSE and README.md).
% Modified 2026-11-24: remove unused occupancy counts; preserve selection.

[~, firstIdx] = unique(pixelCoordinates, 'rows', 'first', 'legacy');
[~, lastIdx] = unique(pixelCoordinates, 'rows', 'last', 'legacy');
end
