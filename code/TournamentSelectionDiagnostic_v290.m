function index = TournamentSelectionDiagnostic_v290(mode,Population,FrontNo,CrowdDis,N)
% Tournament variants for isolating parent-selection implementation effects.

    switch mode
        case 'with_replacement_random_tie'
            candidates = randi(length(Population),2,N);
            index = zeros(1,N);
            for i = 1:N
                index(i) = rankCrowdingWinner(candidates(1,i),candidates(2,i), ...
                    FrontNo,CrowdDis);
            end
        case {'dual_permutation_rank','dual_permutation_dominance'}
            if mod(N,4) ~= 0
                error('Dual-permutation selection requires N divisible by four.');
            end
            permutation1 = randperm(length(Population));
            permutation2 = randperm(length(Population));
            index = zeros(1,N);
            PopObj = Population.objs;
            PopCon = Population.cons;
            for i = 1:4:N
                if strcmp(mode,'dual_permutation_rank')
                    index(i) = rankCrowdingWinner(permutation1(i),permutation1(i+1), ...
                        FrontNo,CrowdDis);
                    index(i+1) = rankCrowdingWinner(permutation1(i+2),permutation1(i+3), ...
                        FrontNo,CrowdDis);
                    index(i+2) = rankCrowdingWinner(permutation2(i),permutation2(i+1), ...
                        FrontNo,CrowdDis);
                    index(i+3) = rankCrowdingWinner(permutation2(i+2),permutation2(i+3), ...
                        FrontNo,CrowdDis);
                else
                    index(i) = dominanceCrowdingWinner(permutation1(i),permutation1(i+1), ...
                        PopObj,PopCon,CrowdDis);
                    index(i+1) = dominanceCrowdingWinner(permutation1(i+2),permutation1(i+3), ...
                        PopObj,PopCon,CrowdDis);
                    index(i+2) = dominanceCrowdingWinner(permutation2(i),permutation2(i+1), ...
                        PopObj,PopCon,CrowdDis);
                    index(i+3) = dominanceCrowdingWinner(permutation2(i+2),permutation2(i+3), ...
                        PopObj,PopCon,CrowdDis);
                end
            end
        otherwise
            error('Unknown tournament mode: %s',mode);
    end
end

function winner = rankCrowdingWinner(a,b,FrontNo,CrowdDis)
    if FrontNo(a) < FrontNo(b)
        winner = a;
    elseif FrontNo(b) < FrontNo(a)
        winner = b;
    elseif CrowdDis(a) > CrowdDis(b)
        winner = a;
    elseif CrowdDis(b) > CrowdDis(a)
        winner = b;
    else
        winner = randomTie(a,b);
    end
end

function winner = dominanceCrowdingWinner(a,b,PopObj,PopCon,CrowdDis)
    relation = constrainedDominance(PopObj(a,:),PopCon(a,:), ...
        PopObj(b,:),PopCon(b,:));
    if relation > 0
        winner = a;
    elseif relation < 0
        winner = b;
    elseif CrowdDis(a) > CrowdDis(b)
        winner = a;
    elseif CrowdDis(b) > CrowdDis(a)
        winner = b;
    else
        winner = randomTie(a,b);
    end
end

function relation = constrainedDominance(objA,conA,objB,conB)
    violationA = sum(max(0,conA));
    violationB = sum(max(0,conB));
    if violationA < violationB
        relation = 1;
    elseif violationB < violationA
        relation = -1;
    elseif all(objA<=objB) && any(objA<objB)
        relation = 1;
    elseif all(objB<=objA) && any(objB<objA)
        relation = -1;
    else
        relation = 0;
    end
end

function winner = randomTie(a,b)
    if rand <= 0.5
        winner = a;
    else
        winner = b;
    end
end
