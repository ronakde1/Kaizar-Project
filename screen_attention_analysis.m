clc;
clear;

csvFile = 'screen_attention_log.csv';
if ~isfile(csvFile)
    error('Missing %s in current folder.', csvFile);
end

data = readtable(csvFile, 'TextType', 'string');
if height(data) < 2
    error('Not enough data in %s.', csvFile);
end

vars = data.Properties.VariableNames;
if ~ismember('unix_time', vars)
    error('CSV must contain a unix_time column.');
end

t = double(data.unix_time);

if ismember('looking_at_screen', vars)
    lookFlag = double(data.looking_at_screen);
elseif ismember('state', vars)
    lookFlag = double(string(data.state) == "LOOKING_AT_SCREEN");
else
    error('CSV must contain either looking_at_screen or state column.');
end

if ismember('state', vars)
    stateText = string(data.state);
else
    stateText = repmat("UNKNOWN", height(data), 1);
end

hasGazeLabel = ismember('gaze_label', vars);
if hasGazeLabel
    gazeLabel = string(data.gaze_label);
else
    gazeLabel = repmat("", height(data), 1);
end

valid = isfinite(t) & isfinite(lookFlag);
t = t(valid);
lookFlag = lookFlag(valid);
stateText = stateText(valid);
gazeLabel = gazeLabel(valid);

if numel(t) < 2
    error('Not enough valid rows after cleaning NaN/Inf values.');
end

[t, order] = sort(t);
lookFlag = lookFlag(order);
stateText = stateText(order);
gazeLabel = gazeLabel(order);

dtRaw = diff(t);
duplicateTimestampCount = sum(dtRaw == 0);
nonIncreasingTimestampCount = sum(dtRaw <= 0);

validDt = dtRaw > 0;
dt = dtRaw(validDt);

if isempty(dt)
    error('No positive time intervals found in unix_time.');
end

intervalStart = t(1:end-1);
intervalStart = intervalStart(validDt);

lookFlagInterval = lookFlag(1:end-1);
lookFlagInterval = lookFlagInterval(validDt);

stateInterval = stateText(1:end-1);
stateInterval = stateInterval(validDt);

if hasGazeLabel
    gazeInterval = gazeLabel(1:end-1);
    gazeInterval = gazeInterval(validDt);
end

abnormalGapThreshold = max(2 * median(dt), 1.0);
abnormalGapCount = sum(dt > abnormalGapThreshold);

totalTime = sum(dt);
lookingTime = sum(dt .* lookFlagInterval);
proportionLooking = lookingTime / totalTime;
percentageLooking = 100 * proportionLooking;

longestFocusStreakSec = maxRunDuration(lookFlagInterval, dt, 1);
longestAwayStreakSec = maxRunDuration(lookFlagInterval, dt, 0);

awayEventThresholdSec = 2.0;
awayEventCount = countRunEvents(lookFlagInterval, dt, 0, awayEventThresholdSec);

eyesClosedEventThresholdSec = 1.0;
if hasGazeLabel
    eyeClosedFlag = gazeInterval == "EYES CLOSED";
    eyesClosedEventCount = countRunEvents(eyeClosedFlag, dt, 1, eyesClosedEventThresholdSec);
else
    eyesClosedEventCount = NaN;
end

eventsPerMinute = awayEventCount / max(totalTime / 60, eps);

relStartSec = intervalStart - t(1);
binIdx = floor(relStartSec / 60) + 1;
nBins = max(binIdx);

minuteStartSec = (0:nBins-1)' * 60;
minuteTotalSec = accumarray(binIdx, dt, [nBins 1], @sum, 0);
minuteLookingSec = accumarray(binIdx, dt .* lookFlagInterval, [nBins 1], @sum, 0);
minutePercent = 100 * (minuteLookingSec ./ max(minuteTotalSec, eps));

minuteTable = table( ...
    minuteStartSec, ...
    minuteTotalSec, ...
    minuteLookingSec, ...
    minutePercent, ...
    'VariableNames', { ...
        'minute_start_sec', ...
        'total_time_sec', ...
        'looking_time_sec', ...
        'focus_percent' ...
    });

cumulativeTimeSec = cumsum(dt);
cumulativeLookingSec = cumsum(dt .* lookFlagInterval);
cumulativeFocusPercent = 100 * (cumulativeLookingSec ./ max(cumulativeTimeSec, eps));

sessionStart = datetime(t(1), 'ConvertFrom', 'posixtime');
sessionEnd = datetime(t(end), 'ConvertFrom', 'posixtime');

summaryTable = table( ...
    sessionStart, ...
    sessionEnd, ...
    totalTime, ...
    lookingTime, ...
    percentageLooking, ...
    longestFocusStreakSec, ...
    longestAwayStreakSec, ...
    awayEventCount, ...
    eventsPerMinute, ...
    eyesClosedEventCount, ...
    duplicateTimestampCount, ...
    nonIncreasingTimestampCount, ...
    abnormalGapCount, ...
    'VariableNames', { ...
        'session_start', ...
        'session_end', ...
        'total_time_sec', ...
        'looking_time_sec', ...
        'focus_percent', ...
        'longest_focus_streak_sec', ...
        'longest_away_streak_sec', ...
        'away_events_over_2s', ...
        'away_events_per_minute', ...
        'eyes_closed_events_over_1s', ...
        'duplicate_timestamp_count', ...
        'non_increasing_timestamp_count', ...
        'abnormal_gap_count' ...
    });

writetable(summaryTable, 'screen_attention_summary.csv');
writetable(minuteTable, 'screen_attention_minute_trend.csv');

fig = figure( ...
    'Color', 'w', ...
    'Name', 'Screen Attention Report', ...
    'NumberTitle', 'off', ...
    'Position', [100 80 1200 760]);

tl = tiledlayout(fig, 2, 2, 'Padding', 'compact', 'TileSpacing', 'compact');

ax1 = nexttile(tl, 1);
stairs(ax1, t - t(1), lookFlag, 'LineWidth', 1.3, 'Color', [0.0 0.45 0.74]);
xlabel(ax1, 'Elapsed Time (s)', 'FontWeight', 'bold');
ylabel(ax1, 'Attention State', 'FontWeight', 'bold');
title(ax1, 'State Timeline', 'FontWeight', 'bold');
ylim(ax1, [-0.1 1.1]);
yticks(ax1, [0 1]);
yticklabels(ax1, {'Not Looking', 'Looking'});
xlim(ax1, [0 max(t - t(1))]);
grid(ax1, 'on');
legend(ax1, 'State', 'Location', 'southoutside');

ax2 = nexttile(tl, 2);
plot(ax2, cumulativeTimeSec, cumulativeFocusPercent, 'LineWidth', 1.8, 'Color', [0.2 0.65 0.35]);
hold(ax2, 'on');
yline(ax2, percentageLooking, '--', sprintf('Final: %.2f%%', percentageLooking), ...
    'Color', [0.2 0.2 0.2], 'LabelHorizontalAlignment', 'left');
xlabel(ax2, 'Elapsed Time (s)', 'FontWeight', 'bold');
ylabel(ax2, 'Cumulative Focus (%)', 'FontWeight', 'bold');
title(ax2, 'Cumulative Focus Percentage Over Time', 'FontWeight', 'bold');
ylim(ax2, [0 100]);
xlim(ax2, [0 max(cumulativeTimeSec)]);
grid(ax2, 'on');
legend(ax2, 'Cumulative Focus', 'Location', 'southoutside');

ax3 = nexttile(tl, 3);
bar(ax3, minuteStartSec / 60, minutePercent, 0.85, 'FaceColor', [0.93 0.56 0.18], 'EdgeColor', 'none');
xlabel(ax3, 'Elapsed Time (minutes)', 'FontWeight', 'bold');
ylabel(ax3, 'Focus in Minute Bin (%)', 'FontWeight', 'bold');
title(ax3, 'Minute-by-Minute Focus', 'FontWeight', 'bold');
ylim(ax3, [0 100]);
if ~isempty(minuteStartSec)
    xlim(ax3, [0 max(1, (minuteStartSec(end) / 60) + 1)]);
end
grid(ax3, 'on');

ax4 = nexttile(tl, 4);
axis(ax4, 'off');
if isnan(eyesClosedEventCount)
    eyesClosedText = 'N/A (gaze_label missing)';
else
    eyesClosedText = sprintf('%d', eyesClosedEventCount);
end

summaryLines = {
    'Session Summary'
    sprintf('Start Time: %s', string(sessionStart))
    sprintf('End Time: %s', string(sessionEnd))
    sprintf('Total Monitored Time: %.2f s', totalTime)
    sprintf('Looking Time: %.2f s', lookingTime)
    sprintf('Overall Focus: %.2f %%', percentageLooking)
    sprintf('Longest Focus Streak: %.2f s', longestFocusStreakSec)
    sprintf('Longest Away Streak: %.2f s', longestAwayStreakSec)
    sprintf('Away Events (>= %.1f s): %d', awayEventThresholdSec, awayEventCount)
    sprintf('Away Events / Minute: %.3f', eventsPerMinute)
    sprintf('Eyes Closed Events (>= %.1f s): %s', eyesClosedEventThresholdSec, eyesClosedText)
    sprintf('Duplicate Timestamps: %d', duplicateTimestampCount)
    sprintf('Non-Increasing Timestamps: %d', nonIncreasingTimestampCount)
    sprintf('Abnormal Gaps (> %.2f s): %d', abnormalGapThreshold, abnormalGapCount)
};

text(ax4, 0.02, 0.98, summaryLines, ...
    'Units', 'normalized', ...
    'VerticalAlignment', 'top', ...
    'FontName', 'Consolas', ...
    'FontSize', 10);

set([ax1 ax2 ax3], 'FontName', 'Arial', 'FontSize', 10, 'LineWidth', 1.0);
sgtitle(tl, sprintf('Screen Attention Report | Overall Focus: %.2f%% | Total Time: %.1fs', percentageLooking, totalTime), ...
    'FontWeight', 'bold');

exportgraphics(fig, 'screen_attention_report.png', 'Resolution', 200);
try
    exportgraphics(fig, 'screen_attention_report.pdf', 'ContentType', 'vector');
catch
    fprintf('PDF export skipped on this MATLAB setup. PNG report was saved.\n');
end

fprintf('Total monitored time: %.2f seconds\n', totalTime);
fprintf('Time looking at screen: %.2f seconds\n', lookingTime);
fprintf('Proportion looking at screen: %.4f\n', proportionLooking);
fprintf('Percentage looking at screen: %.2f%%\n', percentageLooking);
fprintf('Longest focus streak: %.2f seconds\n', longestFocusStreakSec);
fprintf('Longest away streak: %.2f seconds\n', longestAwayStreakSec);
fprintf('Away events (>= %.1fs): %d\n', awayEventThresholdSec, awayEventCount);
fprintf('Away events per minute: %.3f\n', eventsPerMinute);
if isnan(eyesClosedEventCount)
    fprintf('Eyes-closed events: unavailable (gaze_label column not found).\n');
else
    fprintf('Eyes-closed events (>= %.1fs): %d\n', eyesClosedEventThresholdSec, eyesClosedEventCount);
end
fprintf('Duplicate timestamps: %d\n', duplicateTimestampCount);
fprintf('Non-increasing timestamps: %d\n', nonIncreasingTimestampCount);
fprintf('Abnormal gaps (> %.2fs): %d\n', abnormalGapThreshold, abnormalGapCount);
fprintf('Saved: screen_attention_summary.csv, screen_attention_minute_trend.csv, screen_attention_report.png\n');

% Local helpers
function maxDuration = maxRunDuration(flag, dt, targetValue)
maxDuration = 0;
currentDuration = 0;
for i = 1:numel(dt)
    if flag(i) == targetValue
        currentDuration = currentDuration + dt(i);
        maxDuration = max(maxDuration, currentDuration);
    else
        currentDuration = 0;
    end
end
end

function eventCount = countRunEvents(flag, dt, targetValue, minDuration)
eventCount = 0;
currentDuration = 0;
for i = 1:numel(dt)
    if flag(i) == targetValue
        currentDuration = currentDuration + dt(i);
    elseif currentDuration >= minDuration
        eventCount = eventCount + 1;
        currentDuration = 0;
    else
        currentDuration = 0;
    end
end
if currentDuration >= minDuration
    eventCount = eventCount + 1;
end
end