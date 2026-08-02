function A_MPMO_NSGAII_v290(Global)
% <algorithm> <A>
% A-MPMO with NSGA-II environmental selection for PlatEMO v2.9.
% k     --- 3    --- Number of subpopulations
% beta  --- 0.2  --- Switch point from early to later evolution
% delta --- 0.05 --- Minimum later-phase share of each subpopulation
% mode  --- 2    --- Later survival: 1 global floor, 2 global, 3 local
% variant --- 1 --- Internal interpretation variant, see below

% This implementation follows Zhao et al. (2025) on top of the local
% NSGA-II reproduction baseline: SBX, polynomial mutation, NSGA-II
% non-dominated sorting, crowding distance, and random tournament ties.

    %% Parameter setting
    [k,beta,delta,mode,variant] = Global.ParameterSet(3,0.2,0.05,2,1);
    k     = min(Global.N,max(1,round(k)));
    beta  = min(max(beta,0),1);
    delta = min(max(delta,0),1/k);

    proC = [1,   1, 0.5];
    proM = [0.5, 1, 1  ];
    disC = 20;
    disM = 20;

    %% Generate random population and assign skill factors
    Population = Global.Initialization();
    initSizes  = integerSizesFromWeights(ones(1,k),Global.N,1);
    Skill      = makeSkillVector(initSizes);
    SubPop     = splitBySkill(Population,Skill,k);
    contributionWeights = initSizes;

    %% Optimization
    while Global.NotTermination(mergeSubPop(SubPop))
        if Global.evaluated < beta*Global.evaluation
            targetSizes = initSizes;
            SubPop = earlyEvolution(SubPop,targetSizes,proC,proM,disC,disM);
        else
            currentSizes = cellfun(@length,SubPop);
            minSize      = min(max(1,ceil(Global.N*delta)),floor(Global.N/k));
            if variant == 4
                targetSizes = integerSizesFromWeights(contributionWeights,Global.N,minSize);
            else
                targetSizes = integerSizesFromWeights(currentSizes,Global.N,minSize);
            end
            [SubPop,contributionWeights] = laterEvolution(SubPop,targetSizes, ...
                currentSizes,proC,proM,disC,disM,Global.N,minSize,k,mode,variant);
        end
    end
end

function SubPop = earlyEvolution(SubPop,targetSizes,proC,proM,disC,disM)
    k = numel(SubPop);
    for i = 1:k
        target = targetSizes(i);
        if target <= 0
            continue;
        end
        [FrontNo,CrowdDis] = selectionStats(SubPop{i});
        Offspring = makeOffspring(SubPop{i},FrontNo,CrowdDis,target, ...
            paramValue(proC,i),paramValue(proM,i),disC,disM);
        [SubPop{i},~,~] = EnvironmentalSelectionNSGAII_v290( ...
            [SubPop{i},Offspring],target);
    end
end

function [SubPop,nextContribution] = laterEvolution(SubPop,targetSizes,currentSizes,proC,proM,disC,disM,N,minSize,k,mode,variant)
    Parent      = mergeSubPop(SubPop);
    ParentSkill = makeSkillVector(cellfun(@length,SubPop));
    Offspring   = [];
    OffSkill    = [];
    OffSource   = [];

    for i = 1:k
        if variant == 3
            target = currentSizes(i);
        else
            target = targetSizes(i);
        end
        if target <= 0
            continue;
        end
        [FrontNo,CrowdDis] = selectionStats(SubPop{i});
        OffspringI = makeOffspring(SubPop{i},FrontNo,CrowdDis,target, ...
            paramValue(proC,i),paramValue(proM,i),disC,disM);
        Offspring  = [Offspring,OffspringI]; %#ok<AGROW>
        OffSkill   = [OffSkill,repmat(i,1,length(OffspringI))]; %#ok<AGROW>
        OffSource  = [OffSource,ones(1,length(OffspringI))]; %#ok<AGROW>
    end

    if variant == 2 || variant == 3 || mode == 3
        for i = 1:k
            target = targetSizes(i);
            pool = [SubPop{i},Offspring(OffSkill == i)];
            [SubPop{i},~,~] = EnvironmentalSelectionNSGAII_v290(pool,target);
        end
        nextContribution = cellfun(@length,SubPop);
    else
        Pool      = [Parent,Offspring];
        PoolSkill = [ParentSkill,OffSkill];
        PoolSource = [zeros(1,length(Parent)),OffSource];
        if mode == 2
            [Population,Skill,Source] = environmentalSelectionWithSkillsAndSource(Pool,PoolSkill,PoolSource,N);
        else
            [Population,Skill] = environmentalSelectionWithSkillFloor( ...
                Pool,PoolSkill,N,minSize,k);
            Source = zeros(1,length(Population));
        end
        SubPop = splitBySkill(Population,Skill,k);
        if variant == 4
            nextContribution = zeros(1,k);
            for i = 1:k
                nextContribution(i) = sum(Source == 1 & Skill == i);
            end
            if sum(nextContribution) <= 0
                nextContribution = cellfun(@length,SubPop);
            end
        else
            nextContribution = cellfun(@length,SubPop);
        end
    end
end

function Offspring = makeOffspring(Population,FrontNo,CrowdDis,target,proC,proM,disC,disM)
    if isempty(Population)
        Offspring = [];
        return;
    end
    parentCount = 2*ceil(target/2);
    MatingPool  = TournamentSelectionDiagnostic_v290( ...
        'with_replacement_random_tie',Population,FrontNo,CrowdDis,parentCount);
    Offspring = GA(Population(MatingPool),{proC,disC,proM,disM});
    if length(Offspring) > target
        Offspring = Offspring(1:target);
    end
end

function [FrontNo,CrowdDis] = selectionStats(Population)
    if isempty(Population)
        FrontNo = [];
        CrowdDis = [];
        return;
    end
    FrontNo  = NDSort(Population.objs,Population.cons,inf);
    CrowdDis = CrowdingDistance(Population.objs,FrontNo);
end

function [Population,Skill] = environmentalSelectionWithSkillFloor(Population,Skill,N,minSize,k)
    [FrontNo,MaxFNo] = NDSort(Population.objs,Population.cons,N);
    CrowdDis = CrowdingDistance(Population.objs,FrontNo);

    Next = FrontNo < MaxFNo;
    Last = find(FrontNo == MaxFNo);
    [~,Rank] = sort(CrowdDis(Last),'descend');
    need = N - sum(Next);
    if need > 0
        Next(Last(Rank(1:need))) = true;
    end

    counts = zeros(1,k);
    for i = 1:k
        counts(i) = sum(Next & Skill == i);
    end

    for i = 1:k
        while counts(i) < minSize
            candidates = find(~Next & Skill == i);
            if isempty(candidates)
                break;
            end
            add = bestIndex(candidates,FrontNo,CrowdDis);

            replaceable = find(Next);
            keep = false(size(replaceable));
            for r = 1:numel(replaceable)
                s = Skill(replaceable(r));
                keep(r) = counts(s) > minSize;
            end
            replaceable = replaceable(keep);
            if isempty(replaceable)
                break;
            end

            drop = worstIndex(replaceable,FrontNo,CrowdDis);
            Next(drop) = false;
            counts(Skill(drop)) = counts(Skill(drop)) - 1;
            Next(add) = true;
            counts(i) = counts(i) + 1;
        end
    end

    selected = find(Next);
    [~,Order] = sortrows([FrontNo(selected)',-CrowdDis(selected)']);
    selected = selected(Order);
    if numel(selected) > N
        selected = selected(1:N);
    end
    Population = Population(selected);
    Skill      = Skill(selected);
end

function [Population,Skill] = environmentalSelectionWithSkills(Population,Skill,N)
    [Population,Skill,~] = environmentalSelectionWithSkillsAndSource(Population,Skill,zeros(1,length(Population)),N);
end

function [Population,Skill,Source] = environmentalSelectionWithSkillsAndSource(Population,Skill,Source,N)
    [FrontNo,MaxFNo] = NDSort(Population.objs,Population.cons,N);
    CrowdDis = CrowdingDistance(Population.objs,FrontNo);
    Next = FrontNo < MaxFNo;
    Last = find(FrontNo == MaxFNo);
    [~,Rank] = sort(CrowdDis(Last),'descend');
    need = N - sum(Next);
    if need > 0
        Next(Last(Rank(1:need))) = true;
    end
    Population = Population(Next);
    Skill      = Skill(Next);
    Source     = Source(Next);
end

function idx = bestIndex(candidates,FrontNo,CrowdDis)
    [~,Order] = sortrows([FrontNo(candidates)',-CrowdDis(candidates)']);
    idx = candidates(Order(1));
end

function idx = worstIndex(candidates,FrontNo,CrowdDis)
    [~,Order] = sortrows([-FrontNo(candidates)',CrowdDis(candidates)']);
    idx = candidates(Order(1));
end

function value = paramValue(values,i)
    value = values(mod(i-1,numel(values))+1);
end

function sizes = integerSizesFromWeights(weights,total,minSize)
    weights = reshape(weights,1,[]);
    weights = max(weights,0);
    if sum(weights) <= 0
        weights = ones(size(weights));
    end
    weights = weights/sum(weights);

    raw   = max(weights*total,minSize);
    sizes = floor(raw);
    remainder = total - sum(sizes);
    frac = raw - floor(raw);

    while remainder > 0
        [~,idx] = max(frac);
        sizes(idx) = sizes(idx) + 1;
        frac(idx) = -inf;
        remainder = remainder - 1;
    end
    while remainder < 0
        candidates = find(sizes > minSize);
        if isempty(candidates)
            break;
        end
        [~,local] = max(sizes(candidates) - raw(candidates));
        idx = candidates(local);
        sizes(idx) = sizes(idx) - 1;
        remainder = remainder + 1;
    end
end

function Skill = makeSkillVector(sizes)
    Skill = [];
    for i = 1:numel(sizes)
        Skill = [Skill,repmat(i,1,sizes(i))]; %#ok<AGROW>
    end
end

function SubPop = splitBySkill(Population,Skill,k)
    SubPop = cell(1,k);
    for i = 1:k
        SubPop{i} = Population(Skill == i);
    end
end

function Population = mergeSubPop(SubPop)
    Population = [];
    for i = 1:numel(SubPop)
        Population = [Population,SubPop{i}]; %#ok<AGROW>
    end
end
