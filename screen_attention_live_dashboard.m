clc;
clear;

csvFile = 'screen_attention_log.csv';
refreshSec = 1.0;

fig = figure('Name', 'Live Screen Attention Dashboard', ...
             'Color', 'w', ...
             'NumberTitle', 'off', ...
             'Position', [100 100 900 500]);

ax = axes(fig, 'Position', [0.08 0.20 0.86 0.72]);
grid(ax, 'on');
xlabel(ax, 'Time (s)');
ylabel(ax, 'Looking at screen');
title(ax, 'Live Attention Timeline');
ylim(ax, [-0.1 1.1]);

focusText = uicontrol(fig, 'Style', 'text', ...
    'Units', 'normalized', ...
    'Position', [0.70 0.93 0.25 0.05], ...
    'String', 'Focus so far: --.-%', ...
    'FontSize', 12, ...
    'FontWeight', 'bold', ...
    'HorizontalAlignment', 'right', ...
    'BackgroundColor', 'w');

barBg = annotation(fig, 'rectangle', [0.70 0.90 0.25 0.025], ...
    'FaceColor', [0.95 0.95 0.95], ...
    'EdgeColor', [0.3 0.3 0.3]);
barFill = annotation(fig, 'rectangle', [0.70 0.90 0.00 0.025], ...
    'FaceColor', [0.2 0.7 0.25], ...
    'EdgeColor', 'none');

lineHandle = stairs(ax, 0, 0, 'LineWidth', 1.5, 'Color', [0.0 0.45 0.74]);

timerObj = timer( ...
    'ExecutionMode', 'fixedSpacing', ...
    'Period', refreshSec, ...
    'TimerFcn', @updateDashboard, ...
    'ErrorFcn', @timerErrorHandler, ...
    'StopFcn', @timerStopHandler);

setappdata(fig, 'timerObj', timerObj);
setappdata(fig, 'csvFile', csvFile);
setappdata(fig, 'lineHandle', lineHandle);
setappdata(fig, 'ax', ax);
setappdata(fig, 'focusText', focusText);
setappdata(fig, 'barFill', barFill);

fig.CloseRequestFcn = @closeDashboard;
start(timerObj);

fprintf('Live dashboard started. Reading %s every %.1f second(s).\n', csvFile, refreshSec);

function updateDashboard(~, ~)
figLocal = gcf;
if ~isvalid(figLocal)
    return;
end

csvFile = getappdata(figLocal, 'csvFile');
lineHandle = getappdata(figLocal, 'lineHandle');
ax = getappdata(figLocal, 'ax');
focusText = getappdata(figLocal, 'focusText');
barFill = getappdata(figLocal, 'barFill');

if ~isfile(csvFile)
    return;
end

try
    data = readtable(csvFile, 'TextType', 'string');
catch
    return;
end

if height(data) < 2 || ~ismember('unix_time', data.Properties.VariableNames)
    return;
end

t = double(data.unix_time);

if ismember('looking_at_screen', data.Properties.VariableNames)
    lookFlag = double(data.looking_at_screen);
elseif ismember('state', data.Properties.VariableNames)
    lookFlag = double(string(data.state) == "LOOKING_AT_SCREEN");
else
    return;
end

valid = isfinite(t) & isfinite(lookFlag);
t = t(valid);
lookFlag = lookFlag(valid);

if numel(t) < 2
    return;
end

[t, order] = sort(t);
lookFlag = lookFlag(order);

dt = diff(t);
validDt = dt > 0;
dt = dt(validDt);

if isempty(dt)
    return;
end

lookInterval = lookFlag(1:end-1);
lookInterval = lookInterval(validDt);

totalTime = sum(dt);
lookingTime = sum(dt .* lookInterval);
focusPercent = 100 * (lookingTime / max(totalTime, eps));

lineHandle.XData = t - t(1);
lineHandle.YData = lookFlag;
ax.XLim = [0, max(10, lineHandle.XData(end))];

focusText.String = sprintf('Focus so far: %.1f%%', focusPercent);
barFill.Position = [0.70 0.90 0.25 * max(0, min(focusPercent, 100)) / 100 0.025];
end

function closeDashboard(src, ~)
timerObj = getappdata(src, 'timerObj');
if ~isempty(timerObj) && isvalid(timerObj)
    stop(timerObj);
    delete(timerObj);
end
delete(src);
end

function timerErrorHandler(~, evt)
if ~isempty(evt.Data) && isfield(evt.Data, 'Message')
    fprintf('Dashboard timer error: %s\n', evt.Data.Message);
end
end

function timerStopHandler(~, ~)
% Intentionally empty.
end
