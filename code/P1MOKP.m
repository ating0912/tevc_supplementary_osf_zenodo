classdef P1MOKP < PROBLEM
% <problem> <Combinatorial MOP>
% Reproducible bi-objective knapsack instances for the TEVC P1 test bed.
%
% ParameterSet:
%   D             - number of items
%   M             - number of objectives/knapsacks
%   seed          - random seed for reproducible profits and weights
%   capacityRatio - capacity as a fraction of total weight per objective
%   profitMode    - independent, correlated, or conflicting

    properties(Access = private)
        P;
        W;
        C;
    end

    methods
        function obj = P1MOKP()
            [D,M,seed,capacityRatio,profitMode] = obj.Global.ParameterSet(250,2,20260718,0.50,'independent');
            obj.Global.M = M;
            obj.Global.D = D;
            obj.Global.lower = zeros(1,D);
            obj.Global.upper = ones(1,D);
            obj.Global.encoding = 'binary';

            [obj.P,obj.W,obj.C] = P1MOKP.makeData(M,D,seed,capacityRatio,profitMode);
        end

        function PopDec = Init(obj,N)
            density = min(max(mean(obj.C ./ sum(obj.W,2)),0.05),0.80);
            PopDec = rand(N,obj.Global.D) < density;
            PopDec = obj.CalDec(PopDec);
        end

        function PopDec = CalDec(obj,PopDec)
            PopDec = PopDec > 0.5;
            [~,rank] = sort(max(obj.P ./ max(obj.W,eps),[],1),'ascend');
            for i = 1:size(PopDec,1)
                while any(obj.W * PopDec(i,:)' > obj.C)
                    selected = find(PopDec(i,rank),1);
                    if isempty(selected)
                        break;
                    end
                    PopDec(i,rank(selected)) = false;
                end
            end
            PopDec = double(PopDec);
        end

        function PopObj = CalObj(obj,PopDec)
            PopDec = obj.CalDec(PopDec);
            selectedProfit = PopDec * obj.P';
            PopObj = repmat(sum(obj.P,2)',size(PopDec,1),1) - selectedProfit;
        end

        function PopCon = CalCon(obj,PopDec)
            PopDec = PopDec > 0.5;
            loads = PopDec * obj.W';
            PopCon = sum(max(loads - repmat(obj.C',size(PopDec,1),1),0),2);
        end

        function R = PF(obj,N)
            R = sum(obj.P,2)';
        end
    end

    methods(Static)
        function [P,W,C] = makeData(M,D,seed,capacityRatio,profitMode)
            previousState = rng;
            rng(seed,'twister');
            W = randi([10,100],M,D);
            mode = lower(char(profitMode));
            if strcmp(mode,'correlated')
                P = max(10,min(100,round(W + 12*randn(M,D))));
            elseif strcmp(mode,'conflicting') && M == 2
                latent = rand(1,D);
                P = zeros(M,D);
                P(1,:) = 10 + round(90*latent + 8*randn(1,D));
                P(2,:) = 10 + round(90*(1-latent) + 8*randn(1,D));
                P = max(10,min(100,P));
            else
                P = randi([10,100],M,D);
            end
            C = capacityRatio * sum(W,2);
            rng(previousState);
        end
    end
end
