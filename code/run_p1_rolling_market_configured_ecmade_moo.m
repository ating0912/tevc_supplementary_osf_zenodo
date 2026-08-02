% P1 rolling-window market validation: configured ECMADE-MOO protocol.
% Required base variables:
%   P1_ROLLING_METHOD: method name written to the output tree.
%   P1_ROLLING_THETA_ASSIGNMENT: CSV with per-window theta settings.
if ~exist('P1_ROLLING_METHOD','var')
    P1_ROLLING_METHOD = 'Configured_ECMADE_MOO';
end
P1RollingMarketRunner.runAlgorithm(@ECMADE_MOO_KB,P1_ROLLING_METHOD);
