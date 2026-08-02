classdef PortfolioORLIB < PROBLEM
% <problem> <Portfolio>
% OR-Library cardinality-constrained mean-variance portfolio problem.
%
% ParameterSet:
%   dataPath - OR-Library port file path
%   K        - cardinality limit

    properties(Access = private)
        Mu;
        Sigma;
        K;
    end
    methods
        function obj = PortfolioORLIB()
            [dataPath,obj.K] = obj.Global.ParameterSet(fullfile(pwd,'data','orlib','port1.txt'),5);
            [obj.Mu,obj.Sigma] = obj.loadORLibrary(dataPath);
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
            if obj.K < D
                [~,ord] = sort(W,2,'descend');
                mask = false(N,D);
                rows = repelem((1:N)',obj.K,1);
                cols = reshape(ord(:,1:obj.K)',[],1);
                mask(sub2ind([N,D],rows,cols)) = true;
                W(~mask) = 0;
            end
            s = sum(W,2);
            zero = s <= 1e-12;
            if any(zero)
                W(zero,:) = 0;
                keep = min(obj.K,D);
                W(zero,1:keep) = 1/keep;
                s = sum(W,2);
            end
            W = W ./ max(s,1e-12);
        end

        function [mu,Sigma] = loadORLibrary(~,dataPath)
            txt = fileread(dataPath);
            nums = sscanf(txt,'%f');
            idx = 1;
            n = round(nums(idx));
            idx = idx + 1;
            mu = zeros(n,1);
            stdv = zeros(n,1);
            for i = 1:n
                mu(i) = nums(idx);
                stdv(i) = nums(idx+1);
                idx = idx + 2;
            end
            corr = eye(n);
            while idx + 2 <= numel(nums)
                i = round(nums(idx));
                j = round(nums(idx+1));
                rij = nums(idx+2);
                if i >= 1 && i <= n && j >= 1 && j <= n
                    corr(i,j) = rij;
                    corr(j,i) = rij;
                end
                idx = idx + 3;
            end
            Sigma = (stdv*stdv') .* corr;
            Sigma = 0.5*(Sigma+Sigma');
        end
    end
end
