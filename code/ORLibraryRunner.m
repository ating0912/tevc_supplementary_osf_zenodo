classdef ORLibraryRunner
% Shared launcher for the formal OR-Library constrained portfolio subset.

    methods(Static)
        function runAlgorithm(algorithmHandle, method)
            scriptDir = fileparts(mfilename('fullpath'));
            if ORLibraryRunner.baseExists('ORLIB_SMOKE')
                assignin('base','SYNTHETIC_SMOKE',evalin('base','ORLIB_SMOKE'));
            end
            ORLibraryRunner.mapOverride('ORLIB_MANIFEST','SYNTHETIC_MANIFEST');
            ORLibraryRunner.mapOverride('ORLIB_OUT_ROOT','SYNTHETIC_OUT_ROOT');
            ORLibraryRunner.mapOverride('ORLIB_RUNS','SYNTHETIC_RUNS');
            ORLibraryRunner.mapOverride('ORLIB_N','SYNTHETIC_N');
            ORLibraryRunner.mapOverride('ORLIB_MAXFE','SYNTHETIC_MAXFE');
            ORLibraryRunner.mapOverride('ORLIB_MAX_INSTANCES','SYNTHETIC_MAX_INSTANCES');
            ORLibraryRunner.mapOverride('ORLIB_INSTANCE_NAMES','SYNTHETIC_INSTANCE_NAMES');
            ORLibraryRunner.mapOverride('ORLIB_SKIP_SUMMARY','SYNTHETIC_SKIP_SUMMARY');
            ORLibraryRunner.mapOverride('ORLIB_FORCE_RERUN','SYNTHETIC_FORCE_RERUN');

            if ~ORLibraryRunner.baseExists('SYNTHETIC_MANIFEST')
                assignin('base','SYNTHETIC_MANIFEST', ...
                    fullfile(scriptDir,'data','orlib_constrained_portfolio','manifest.csv'));
            end
            if ~ORLibraryRunner.baseExists('SYNTHETIC_OUT_ROOT')
                if ORLibraryRunner.baseExists('SYNTHETIC_SMOKE') && evalin('base','SYNTHETIC_SMOKE')
                    outRoot = fullfile(scriptDir,'p0_lite_outputs','orlib_constrained_portfolio_smoke');
                else
                    outRoot = fullfile(scriptDir,'p0_lite_outputs','orlib_constrained_portfolio');
                end
                assignin('base','SYNTHETIC_OUT_ROOT',outRoot);
            end
            if ~ORLibraryRunner.baseExists('SYNTHETIC_SPLITS')
                assignin('base','SYNTHETIC_SPLITS',{'test'});
            end
            assignin('base','SYNTHETIC_EXPERIMENT_NAME','orlib_constrained_portfolio');
            assignin('base','SYNTHETIC_DATASET_LABEL','OR-Library');

            SyntheticRunner.runAlgorithm(algorithmHandle,method);
        end

        function mapOverride(sourceName,targetName)
            if ORLibraryRunner.baseExists(sourceName)
                assignin('base',targetName,evalin('base',sourceName));
            end
        end

        function tf = baseExists(varName)
            tf = evalin('base',sprintf('exist(''%s'',''var'')',varName)) ~= 0;
        end
    end
end
