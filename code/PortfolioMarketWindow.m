classdef PortfolioMarketWindow < PROBLEM
% <problem> <Portfolio>
% Rolling-window market mean-variance portfolio problem.

    properties(Access = private)
        Mu;
        Sigma;
        K;
    end

    methods
        function obj = PortfolioMarketWindow()
            [dataPath,obj.K] = obj.Global.ParameterSet(fullfile(pwd,'window.mat'),10);
            data = load(dataPath,'mu','Sigma');
            obj.Mu = data.mu(:);
            obj.Sigma = 0.5*(data.Sigma + data.Sigma');
            obj.Global.M = 2;
            obj.Global.D = numel(obj.Mu);
            obj.Global.lower = zeros(1,obj.Global.D);
            obj.Global.upper = ones(1,obj.Global.D);
            obj.Global.encoding = 'real';
        end

        function PopDec = Init(obj,N)
            PopDec = rand(N,obj.Global.D);
            PopDec = obj.repairPortfolio(PopDec);
        end

        function PopDec = CalDec(obj,PopDec)
            PopDec = obj.repairPortfolio(PopDec);
        end

        function PopObj = CalObj(obj,PopDec)
            PopDec = obj.repairPortfolio(PopDec);
            risk = sum((PopDec*obj.Sigma).*PopDec,2);
            ret = PopDec*obj.Mu(:);
            PopObj = [risk,-ret];
        end

        function PopCon = CalCon(obj,PopDec)
            W = obj.repairPortfolio(PopDec);
            cardViolation = max(sum(W > 1e-12,2) - obj.K,0);
            sumViolation = abs(sum(W,2)-1);
            PopCon = cardViolation + sumViolation;
        end
    end

    methods(Access = private)
        function W = repairPortfolio(obj,W)
            W = max(min(W,1),0);
            [N,D] = size(W);
            keep = min(obj.K,D);
            if keep < D
                [~,ord] = sort(W,2,'descend');
                mask = false(N,D);
                rows = repelem((1:N)',keep,1);
                cols = reshape(ord(:,1:keep)',[],1);
                mask(sub2ind([N,D],rows,cols)) = true;
                W(~mask) = 0;
            end
            s = sum(W,2);
            zero = s <= 1e-12;
            if any(zero)
                W(zero,:) = 0;
                W(zero,1:keep) = 1/keep;
                s = sum(W,2);
            end
            W = W ./ max(s,1e-12);
        end
    end
end
