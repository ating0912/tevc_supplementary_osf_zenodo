function D = pdist2(X,Y,varargin)
%PDIST2 Minimal Euclidean pdist2 replacement for PlatEMO experiments.
%   D = PDIST2(X,Y) returns pairwise Euclidean distances between rows of X
%   and rows of Y. This lightweight fallback avoids requiring the
%   Statistics and Machine Learning Toolbox for SPEA2's CalFitness.

    if nargin < 2
        Y = X;
    end
    if ~isempty(varargin)
        metric = varargin{1};
        if ischar(metric) || isstring(metric)
            if ~strcmpi(char(metric),'euclidean')
                error('pdist2:fallbackMetric','Fallback pdist2 only supports Euclidean distance.');
            end
        end
    end
    X = double(X);
    Y = double(Y);
    XX = sum(X.^2,2);
    YY = sum(Y.^2,2)';
    D2 = bsxfun(@plus,XX,YY) - 2*(X*Y');
    D = sqrt(max(D2,0));
end
