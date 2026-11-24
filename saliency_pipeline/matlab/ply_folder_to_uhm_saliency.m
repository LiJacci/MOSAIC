%% Batch PLY -> RR-CAP six-view RGB projection -> UHM saliency -> PNG
% Entry point: edit the configuration below, then run this script.
% Output: outputRoot/<relative_folder>/<ply_name>/<ply_name>_sMap_1..6.png
% Projection order: XY min/max Z, YZ min/max X, ZX min/max Y.

clear; clc;

%% ===================== User configuration =====================
% Input/output paths are relative to the MATLAB working directory unless absolute.
inputRoot  = 'WPC2.0';
outputRoot = 'wpc2.0_saliency';

% Bundled runtime dependencies, resolved relative to this script.
scriptDir = fileparts(mfilename('fullpath'));
rrcapRoot = fullfile(fileparts(scriptDir), 'repos', 'RR-CAP');
uhmRoot   = fullfile(fileparts(scriptDir), 'repos', 'UHM');

% UHM option. true follows UHM default center-bias post-processing.
useCenterBias = true;

% Set true if you also want to save the six projected RGB images.
saveProjectionImages = false;

% If false, existing saliency maps are skipped.
overwriteExisting = true;

% Debug: set to a positive integer to process only the first N ply files.
limit = 0;
%% ==============================================================

inputRoot = char(inputRoot);
outputRoot = char(outputRoot);
rrcapRoot = char(rrcapRoot);
uhmRoot = char(uhmRoot);

if exist(inputRoot, 'dir') ~= 7
    error('Input folder does not exist: %s', inputRoot);
end
if exist(outputRoot, 'dir') ~= 7
    mkdir(outputRoot);
end
if exist(rrcapRoot, 'dir') ~= 7
    error('RR-CAP folder does not exist: %s', rrcapRoot);
end
if exist(uhmRoot, 'dir') ~= 7
    error('UHM folder does not exist: %s', uhmRoot);
end

addpath(rrcapRoot);
addpath(uhmRoot);
addpath(genpath(fullfile(uhmRoot, 'src')));

plyFiles = listPlyRecursive(inputRoot);
if limit > 0 && numel(plyFiles) > limit
    plyFiles = plyFiles(1:limit);
end

fprintf('[INFO] Found %d ply files.\n', numel(plyFiles));
fprintf('[INFO] Input : %s\n', inputRoot);
fprintf('[INFO] Output: %s\n', outputRoot);

for fileIdx = 1:numel(plyFiles)
    plyPath = plyFiles{fileIdx};
    [plyDir, plyName, ~] = fileparts(plyPath);
    relDir = relativeDir(inputRoot, plyDir);
    outDir = fullfile(outputRoot, relDir, plyName);
    if exist(outDir, 'dir') ~= 7
        mkdir(outDir);
    end

    fprintf('\n[%d/%d] %s\n', fileIdx, numel(plyFiles), plyPath);

    expectedDone = true;
    for viewIdx = 1:6
        outMap = fullfile(outDir, sprintf('%s_sMap_%d.png', plyName, viewIdx));
        if exist(outMap, 'file') ~= 2
            expectedDone = false;
            break;
        end
    end
    if expectedDone && ~overwriteExisting
        fprintf('  Skip existing maps.\n');
        continue;
    end

    try
        pc = pcread(plyPath);
        if isempty(pc.Color)
            pc = pointCloud(pc.Location, 'Color', uint8(255 * ones(pc.Count, 3)));
        end
        projectedViews = getProjection(pc);

        for viewIdx = 1:6
            rgbView = uint8(projectedViews{viewIdx});
            outMap = fullfile(outDir, sprintf('%s_sMap_%d.png', plyName, viewIdx));

            if exist(outMap, 'file') == 2 && ~overwriteExisting
                fprintf('  View %d exists, skip.\n', viewIdx);
                continue;
            end

            fprintf('  View %d: projection -> UHM saliency\n', viewIdx);
            saliency = computeUhmSaliencyFromImage(rgbView, uhmRoot, useCenterBias);
            saliency = safeNormalize01(saliency);
            imwrite(uint8(round(255 * saliency)), outMap);

            if saveProjectionImages
                outProjection = fullfile(outDir, sprintf('%s_proj_%d.png', plyName, viewIdx));
                imwrite(rgbView, outProjection);
            end
        end
    catch ME
        warning('Failed on %s\nReason: %s', plyPath, ME.message);
    end
end

fprintf('\n[DONE] Saliency maps written to %s\n', outputRoot);

%% ===================== Local helper functions =====================
function saliency = computeUhmSaliencyFromImage(rgbImage, uhmRoot, useCenterBias)
% UHM's setup_globalSetting() assumes that pwd is the UHM repository root,
% because it sets basesPath = [pwd filesep 'bases' filesep].
oldDir = pwd;
cleanupObj = onCleanup(@() cd(oldDir));
cd(uhmRoot);
rgbImage = im2double(rgbImage);
saliency = computeSaliency(rgbImage, useCenterBias);
saliency = double(saliency);
end

function files = listPlyRecursive(rootDir)
files = {};
items = dir(rootDir);
for i = 1:numel(items)
    name = items(i).name;
    if strcmp(name, '.') || strcmp(name, '..')
        continue;
    end
    fullPath = fullfile(rootDir, name);
    if items(i).isdir
        subFiles = listPlyRecursive(fullPath);
        files = [files, subFiles]; %#ok<AGROW>
    else
        [~, ~, ext] = fileparts(name);
        if strcmpi(ext, '.ply')
            files{end+1} = fullPath; %#ok<AGROW>
        end
    end
end
files = sort(files);
end

function rel = relativeDir(rootDir, childDir)
rootDir = char(java.io.File(rootDir).getCanonicalPath());
childDir = char(java.io.File(childDir).getCanonicalPath());
if numel(childDir) < numel(rootDir) || ~strcmpi(childDir(1:numel(rootDir)), rootDir)
    rel = '';
    return;
end
rel = childDir(numel(rootDir)+1:end);
if ~isempty(rel) && (rel(1) == filesep || rel(1) == '/' || rel(1) == '\')
    rel = rel(2:end);
end
end

function out = safeNormalize01(in)
in = double(in);
in(~isfinite(in)) = 0;
mn = min(in(:));
mx = max(in(:));
if mx > mn
    out = (in - mn) ./ (mx - mn);
else
    out = zeros(size(in));
end
end
