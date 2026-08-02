function ECMADE_MOO_TUNE_CONSERVATIVE(Global)
% <algorithm> <E>
% ECMADE-MOO with multi-subpopulation adaptive DE and NSGA-II selection.
% This MATLAB/PlatEMO version follows the local ecmade_moo.py design:
% individual-level adaptive F/CR memory, Pareto archive monitoring, and
% stagnation-triggered elite exchange.

    %% Configuration aligned with ecmade_moo.py
    subpops              = 3;
    archiveSize          = 20;
    theta                = 1/13;
    stagnationThreshold  = 50;
    exploitationAlpha    = 0.8;
    initMuF              = [0.9 0.8 0.8];
    initMuCR             = [0.9 0.5 0.5];
    fScale               = 0.05;
    crScale              = 0.05;
    fMax                 = 0.75;
    exchangeMode         = 'paper';
    consensusArchive     = false;
    consensusBins        = 24;
    archiveConsWeight    = 0.0;
    bestGuide            = 'rank';
    bestConsWeight       = 0.55;
    bestCentralWeight    = 0.30;
    minSubpopSize        = 1;

    %% Generate random population
    Population = Global.Initialization();
    subpopIDs  = initialSubpopIDs(Global.N,subpops);
    muF        = initMuF(mod(subpopIDs-1,numel(initMuF))+1)';
    muCR       = initMuCR(mod(subpopIDs-1,numel(initMuCR))+1)';
    recentF    = cell(Global.N,1);
    recentCR   = cell(Global.N,1);
    generation = 0;
    stagnation = 0;
    exchanges  = 0; %#ok<NASGU>

    [archiveDec,archiveObj,archiveHits,archiveMasks] = updateParetoArchive( ...
        [],[],[],[],Population,subpopIDs,Global.N,consensusArchive,consensusBins,archiveConsWeight,subpops);

    %% Optimization
    while Global.NotTermination(Population)
        generation = generation + 1;
        PopDec = Population.decs;
        PopObj = Population.objs;
        PopCon = Population.cons;
        bestGuides = selectBestGuides(PopObj,PopCon,subpopIDs,bestGuide, ...
            consensusArchive,consensusBins,bestConsWeight,bestCentralWeight,subpops);

        OffDec = [];
        offSubpopIDs = [];
        parentIdx = [];
        trialSID = [];
        trialF = [];
        trialCR = [];

        for sid = 1:subpops
            members = find(subpopIDs == sid);
            for mi = 1:numel(members)
                if Global.evaluated + size(OffDec,1) >= Global.evaluation
                    break;
                end
                i = members(mi);
                Fi = sampleF(muF(i),fScale,fMax);
                CRi = sampleCR(muCR(i),crScale);
                bestIndex = bestGuides(sid);
                mutant = mutateECMADEPythonStyle(i,sid,PopDec,subpopIDs,bestIndex,Fi, ...
                    generation,Global.evaluation,Global.N,exploitationAlpha);
                mutant = clipToBounds(mutant,Global.lower,Global.upper);
                trial = binomialCrossover(PopDec(i,:),mutant,CRi);
                trial = clipToBounds(trial,Global.lower,Global.upper);

                OffDec(end+1,:) = trial; %#ok<AGROW>
                offSubpopIDs(end+1,1) = sid; %#ok<AGROW>
                parentIdx(end+1,1) = i; %#ok<AGROW>
                trialSID(end+1,1) = sid; %#ok<AGROW>
                trialF(end+1,1) = Fi; %#ok<AGROW>
                trialCR(end+1,1) = CRi; %#ok<AGROW>
            end
        end

        if isempty(OffDec)
            break;
        end

        Offspring = INDIVIDUAL(OffDec);
        Pool = [Population,Offspring];
        poolSubpopIDs = [subpopIDs(:); offSubpopIDs(:)];
        poolMuF = [muF(:); muF(parentIdx(:))];
        poolMuCR = [muCR(:); muCR(parentIdx(:))];
        poolRecentF = [recentF(:); recentF(parentIdx(:))];
        poolRecentCR = [recentCR(:); recentCR(parentIdx(:))];

        selected = ecmadeEnvironmentalSelection(Pool,Global.N);

        survivedOffspring = selected(selected > numel(Population)) - numel(Population);
        for k = 1:numel(survivedOffspring)
            t = survivedOffspring(k);
            poolIndex = numel(Population) + t;
            sid = trialSID(t); %#ok<NASGU>
            poolRecentF{poolIndex} = appendRecent(poolRecentF{poolIndex},trialF(t),generation,archiveSize);
            poolRecentCR{poolIndex} = appendRecent(poolRecentCR{poolIndex},trialCR(t),generation,archiveSize);
            poolMuF(poolIndex) = (1-theta)*poolMuF(poolIndex) + ...
                theta*weightedLehmerMean(poolRecentF{poolIndex},generation);
            poolMuCR(poolIndex) = (1-theta)*poolMuCR(poolIndex) + ...
                theta*weightedArithmeticMean(poolRecentCR{poolIndex},generation);
            poolMuF(poolIndex) = min(max(poolMuF(poolIndex),1e-8),fMax);
            poolMuCR(poolIndex) = min(max(poolMuCR(poolIndex),0),1);
        end

        Population = Pool(selected);
        subpopIDs = poolSubpopIDs(selected);
        muF = poolMuF(selected);
        muCR = poolMuCR(selected);
        recentF = poolRecentF(selected);
        recentCR = poolRecentCR(selected);
        subpopIDs = ensureSubpopBalance(subpopIDs,Population.objs,Population.cons,subpops,minSubpopSize);

        [newArchiveDec,newArchiveObj,newArchiveHits,newArchiveMasks,archiveChanged] = updateParetoArchive( ...
            archiveDec,archiveObj,archiveHits,archiveMasks,Population,subpopIDs,Global.N, ...
            consensusArchive,consensusBins,archiveConsWeight,subpops);
        archiveDec = newArchiveDec;
        archiveObj = newArchiveObj;
        archiveHits = newArchiveHits;
        archiveMasks = newArchiveMasks;
        if archiveChanged
            stagnation = 0;
        else
            stagnation = stagnation + 1;
        end

        if stagnationThreshold > 0 && stagnation > stagnationThreshold
            [Population,subpopIDs,muF,muCR,recentF,recentCR] = exchangeInformation( ...
                Population,subpopIDs,muF,muCR,recentF,recentCR,subpops,exchangeMode);
            stagnation = 0;
            exchanges = exchanges + 1; %#ok<NASGU>
        end
    end
end

function ids = initialSubpopIDs(N,subpops)
    ids = mod(randperm(N)-1,subpops) + 1;
    ids = ids(:);
end

function mutant = mutateECMADEPythonStyle(i,sid,PopDec,subpopIDs,bestIndex,F,generation,maxFE,popSize,alpha)
    members = find(subpopIDs == sid);
    best = PopDec(bestIndex,:);
    if mod(sid-1,3) == 0
        r = chooseIndicesFromSubpop(members,i,5);
        mutant = PopDec(r(1),:) + F*(PopDec(r(2),:)-PopDec(r(3),:)) + ...
            F*(PopDec(r(4),:)-PopDec(r(5),:));
    elseif mod(sid-1,3) == 1
        r = chooseIndicesFromSubpop(members,i,4);
        mutant = alpha*best + F*(PopDec(r(1),:)-PopDec(r(2),:)) + ...
            F*(PopDec(r(3),:)-PopDec(r(4),:));
    else
        r = chooseIndicesFromSubpop(members,i,5);
        omega = min(1,generation/max(1,maxFE/max(1,popSize)));
        rand1 = PopDec(r(1),:) + F*(PopDec(r(2),:)-PopDec(r(3),:));
        currentToBest = PopDec(i,:) + F*(best-PopDec(i,:)) + F*(PopDec(r(4),:)-PopDec(r(5),:));
        mutant = (1-omega)*rand1 + omega*currentToBest;
    end
end

function r = chooseIndicesFromSubpop(members,excluded,count)
    pool = members(members ~= excluded);
    if isempty(pool)
        pool = members;
    end
    if numel(pool) >= count
        pool = pool(randperm(numel(pool)));
        r = pool(1:count);
    else
        r = pool(randi(numel(pool),1,count));
    end
end

function Fi = sampleF(mu,fScale,fMax)
    Fi = mu + fScale*tan(pi*(rand-0.5));
    tries = 0;
    while Fi <= 0 && tries < 100
        Fi = mu + fScale*tan(pi*(rand-0.5));
        tries = tries + 1;
    end
    Fi = min(max(Fi,1e-8),fMax);
end

function CRi = sampleCR(mu,crScale)
    CRi = min(max(mu + crScale*randn,0),1);
end

function trial = binomialCrossover(target,mutant,CR)
    D = numel(target);
    mask = rand(1,D) <= CR;
    mask(randi(D)) = true;
    trial = target;
    trial(mask) = mutant(mask);
end

function X = clipToBounds(X,lower,upper)
    X = min(max(X,lower),upper);
end

function recent = appendRecent(recent,value,generation,archiveSize)
    if isempty(recent)
        recent = [value,generation];
    else
        recent(end+1,:) = [value,generation];
    end
    if size(recent,1) > archiveSize
        recent = recent(end-archiveSize+1:end,:);
    end
end

function m = weightedLehmerMean(values,currentGeneration)
    data = values(:,1);
    weights = successfulParameterWeights(values,currentGeneration);
    denom = sum(weights.*data);
    if denom > 0
        m = sum(weights.*data.*data)/denom;
    else
        m = mean(data);
    end
end

function m = weightedArithmeticMean(values,currentGeneration)
    data = values(:,1);
    weights = successfulParameterWeights(values,currentGeneration);
    m = sum(weights.*data);
end

function weights = successfulParameterWeights(values,currentGeneration)
    generations = values(:,2);
    weights = exp(generations/max(currentGeneration,1)-1);
    total = sum(weights);
    if total <= 0
        weights = ones(size(generations))/max(numel(generations),1);
    else
        weights = weights/total;
    end
end

function order = rankOrder(Obj,Con)
    [FrontNo,~] = NDSort(Obj,Con,size(Obj,1));
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    [~,order] = sortrows([FrontNo(:),-CrowdDis(:)],[1 2]);
end

function guides = selectBestGuides(Obj,Con,ids,bestGuide,consensusArchive,consensusBins,bestConsWeight,bestCentralWeight,subpops)
    guide = lower(bestGuide);
    if strcmp(guide,'rank')
        order = rankOrder(Obj,Con);
        guides = repmat(order(1),subpops,1);
        return;
    elseif strcmp(guide,'consensus')
        bestIndex = selectConsensusBest(Obj,Con,ids,consensusArchive,consensusBins,bestConsWeight,bestCentralWeight,subpops);
        guides = repmat(bestIndex,subpops,1);
        return;
    elseif strcmp(guide,'ideal')
        bestIndex = selectIdealBest(Obj,Con);
        guides = repmat(bestIndex,subpops,1);
        return;
    elseif strcmp(guide,'reference')
        guides = selectReferenceBestGuides(Obj,Con,ids,subpops);
        return;
    else
        error('ECMADE_MOO:InvalidBestGuide','bestGuide must be rank, ideal, consensus, or reference.');
    end
end

function bestIndex = selectIdealBest(Obj,Con)
    [FrontNo,~] = NDSort(Obj,Con,size(Obj,1));
    front = find(FrontNo == 1);
    if isempty(front)
        order = rankOrder(Obj,Con);
        bestIndex = order(1);
        return;
    end
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    normalized = normalizeObjectives(Obj);
    distance = sqrt(sum(normalized(front,:).^2,2));
    crowdVals = CrowdDis(front);
    [~,order] = sortrows([distance(:),-crowdVals(:)],[1 2]);
    bestIndex = front(order(1));
end

function bestIndex = selectConsensusBest(Obj,Con,ids,consensusArchive,consensusBins,bestConsWeight,bestCentralWeight,subpops)
    if ~consensusArchive
        order = rankOrder(Obj,Con);
        bestIndex = order(1);
        return;
    end
    [FrontNo,~] = NDSort(Obj,Con,size(Obj,1));
    front = find(FrontNo == 1);
    if isempty(front)
        order = rankOrder(Obj,Con);
        bestIndex = order(1);
        return;
    end
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    hits = ones(size(Obj,1),1);
    masks = subpopMasks(ids,subpops);
    consensus = consensusScores(Obj,hits,masks,consensusBins,subpops);
    centrality = centralityScores(Obj);
    crowdNorm = normalizedCrowding(CrowdDis);
    crowdWeight = max(0,1 - bestConsWeight - bestCentralWeight);
    score = bestConsWeight*consensus + bestCentralWeight*centrality + crowdWeight*crowdNorm;
    [~,pos] = max(score(front));
    bestIndex = front(pos);
end

function guides = selectReferenceBestGuides(Obj,Con,ids,subpops)
    [FrontNo,~] = NDSort(Obj,Con,size(Obj,1));
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    front = find(FrontNo == 1);
    if isempty(front)
        order = rankOrder(Obj,Con);
        guides = repmat(order(1),subpops,1);
        return;
    end
    normalized = normalizeObjectives(Obj);
    weights = referenceWeights(subpops,size(Obj,2));
    guides = zeros(subpops,1);
    for sid = 1:subpops
        local = front(ids(front) == sid);
        if isempty(local)
            candidates = front;
        else
            candidates = local;
        end
        scalar = max(weights(sid,:).*normalized(candidates,:),[],2);
        crowdVals = CrowdDis(candidates);
        [~,order] = sortrows([scalar(:),-crowdVals(:)],[1 2]);
        guides(sid) = candidates(order(1));
    end
end

function normObj = normalizeObjectives(Obj)
    lo = min(Obj,[],1);
    hi = max(Obj,[],1);
    span = hi - lo;
    span(span <= 0) = 1;
    normObj = min(max((Obj - lo)./span,0),1);
end

function weights = referenceWeights(k,m)
    epsVal = 1e-3;
    if m == 2
        if k == 1
            weights = [0.5 0.5];
        else
            t = linspace(0,1,k)';
            weights = [1-t,t];
        end
    else
        rng(12345 + k + m);
        raw = -log(max(rand(k,m),realmin));
        weights = raw./sum(raw,2);
    end
    weights = max(weights,epsVal);
    weights = weights./sum(weights,2);
end

function selected = ecmadeEnvironmentalSelection(Population,N)
    [FrontNo,MaxFNo] = NDSort(Population.objs,Population.cons,N);
    Next = FrontNo < MaxFNo;
    CrowdDis = CrowdingDistance(Population.objs,FrontNo);
    Last = find(FrontNo == MaxFNo);
    [~,Rank] = sort(CrowdDis(Last),'descend');
    remain = N - sum(Next);
    if remain > 0
        Next(Last(Rank(1:remain))) = true;
    end
    selected = find(Next);
end

function ids = ensureSubpopBalance(ids,Obj,Con,subpops,minSubpopSize)
    ids = ids(:);
    [FrontNo,~] = NDSort(Obj,Con,size(Obj,1));
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    [~,worstOrder] = sortrows([-FrontNo(:),CrowdDis(:)],[1 2]);
    minSize = min(minSubpopSize,floor(numel(ids)/max(1,subpops)));
    for sid = 1:subpops
        while sum(ids == sid) < minSize
            counts = histcounts(ids,1:subpops+1);
            donors = find(counts > minSize);
            if isempty(donors)
                [~,donor] = max(counts);
            else
                [~,pos] = max(counts(donors));
                donor = donors(pos);
            end
            candidates = worstOrder(ids(worstOrder) == donor);
            if ~isempty(candidates)
                ids(candidates(1)) = sid;
            else
                ids(randi(numel(ids))) = sid;
            end
        end
    end
end

function [archiveDec,archiveObj,archiveHits,archiveMasks,changed] = updateParetoArchive(oldDec,oldObj,oldHits,oldMasks,Population,ids,N,consensusArchive,consensusBins,archiveConsWeight,subpops)
    if isempty(oldObj)
        mergedDec = Population.decs;
        mergedObj = Population.objs;
        mergedHits = ones(size(mergedObj,1),1);
        mergedMasks = subpopMasks(ids,subpops);
        oldKeys = {};
    else
        mergedDec = [oldDec; Population.decs];
        mergedObj = [oldObj; Population.objs];
        mergedHits = [oldHits(:); ones(numel(Population),1)];
        mergedMasks = [oldMasks(:); subpopMasks(ids,subpops)];
        oldKeys = objectiveKeys(oldObj);
    end
    [FrontNo,~] = NDSort(mergedObj,zeros(size(mergedObj,1),1),size(mergedObj,1));
    nd = FrontNo == 1;
    archiveDec = mergedDec(nd,:);
    archiveObj = mergedObj(nd,:);
    archiveHits = mergedHits(nd);
    archiveMasks = mergedMasks(nd);
    [keep,archiveHits,archiveMasks] = uniqueArchiveRows(archiveObj,archiveHits,archiveMasks);
    archiveDec = archiveDec(keep,:);
    archiveObj = archiveObj(keep,:);
    limit = max(N*5,N);
    if size(archiveObj,1) > limit
        selected = archivePruningIndices(archiveObj,archiveHits,archiveMasks,limit, ...
            consensusArchive,consensusBins,archiveConsWeight,subpops);
        archiveDec = archiveDec(selected,:);
        archiveObj = archiveObj(selected,:);
        archiveHits = archiveHits(selected);
        archiveMasks = archiveMasks(selected);
    end
    newKeys = objectiveKeys(archiveObj);
    changed = numel(oldKeys) ~= numel(newKeys) || ~all(strcmp(sort(oldKeys),sort(newKeys)));
end

function selected = archivePruningIndices(Obj,hits,masks,N,consensusArchive,consensusBins,archiveConsWeight,subpops)
    if ~consensusArchive
        selected = environmentalSelectionFromObj(Obj,N);
        return;
    end
    consensus = consensusScores(Obj,hits,masks,consensusBins,subpops);
    crowdNorm = normalizedCrowding(crowdingDistanceStandalone(Obj));
    score = archiveConsWeight*consensus + (1-archiveConsWeight)*crowdNorm;
    [~,order] = sort(score,'descend');
    selected = order(1:N);
end

function selected = environmentalSelectionFromObj(Obj,N)
    [FrontNo,MaxFNo] = NDSort(Obj,zeros(size(Obj,1),1),N);
    Next = FrontNo < MaxFNo;
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    Last = find(FrontNo == MaxFNo);
    [~,Rank] = sort(CrowdDis(Last),'descend');
    remain = N - sum(Next);
    if remain > 0
        Next(Last(Rank(1:remain))) = true;
    end
    selected = find(Next);
end

function keep = uniqueObjectiveRows(Obj)
    rounded = round(Obj*1e12)/1e12;
    [~,keep] = unique(rounded,'rows','stable');
end

function [keep,combinedHits,combinedMasks] = uniqueArchiveRows(Obj,hits,masks)
    rounded = round(Obj*1e12)/1e12;
    keep = [];
    combinedHits = [];
    combinedMasks = [];
    keys = {};
    for i = 1:size(rounded,1)
        key = sprintf('%.12g,',rounded(i,:));
        pos = find(strcmp(keys,key),1);
        if isempty(pos)
            keys{end+1,1} = key; %#ok<AGROW>
            keep(end+1,1) = i; %#ok<AGROW>
            combinedHits(end+1,1) = hits(i); %#ok<AGROW>
            combinedMasks(end+1,1) = masks(i); %#ok<AGROW>
        else
            combinedHits(pos) = combinedHits(pos) + hits(i);
            combinedMasks(pos) = double(bitor(uint32(combinedMasks(pos)),uint32(masks(i))));
        end
    end
end

function masks = subpopMasks(ids,subpops)
    ids = ids(:);
    masks = zeros(numel(ids),1);
    for i = 1:numel(ids)
        bit = max(0,min(subpops-1,ids(i)-1));
        masks(i) = 2^bit;
    end
end

function scores = consensusScores(Obj,hits,masks,consensusBins,subpops)
    if isempty(Obj)
        scores = [];
        return;
    end
    cells = objectiveCells(Obj,consensusBins);
    [~,~,group] = unique(cells,'rows','stable');
    cellHits = accumarray(group,hits(:),[],@sum);
    cellMasks = zeros(max(group),1);
    for i = 1:numel(group)
        cellMasks(group(i)) = bitor(uint32(cellMasks(group(i))),uint32(masks(i)));
    end
    maxHits = max(cellHits);
    if maxHits <= 0
        maxHits = 1;
    end
    scores = zeros(size(Obj,1),1);
    for i = 1:size(Obj,1)
        subpopScore = bitCount(cellMasks(group(i))) / max(subpops,1);
        hitScore = log1p(cellHits(group(i))) / max(log1p(maxHits),1e-12);
        scores(i) = 0.65*subpopScore + 0.35*hitScore;
    end
end

function cells = objectiveCells(Obj,consensusBins)
    lo = min(Obj,[],1);
    hi = max(Obj,[],1);
    span = hi - lo;
    span(span <= 0) = 1;
    scaled = min(max((Obj - lo)./span,0),1);
    bins = max(2,consensusBins);
    cells = min(floor(scaled*bins),bins-1);
end

function scores = centralityScores(Obj)
    if isempty(Obj)
        scores = [];
        return;
    end
    lo = min(Obj,[],1);
    hi = max(Obj,[],1);
    span = hi - lo;
    span(span <= 0) = 1;
    scaled = (Obj - lo)./span;
    center = median(scaled,1);
    dist = sqrt(sum((scaled - center).^2,2));
    maxDist = max(dist);
    if maxDist <= 0
        scores = ones(size(Obj,1),1);
    else
        scores = 1 - dist/maxDist;
    end
    scores = min(max(scores,0),1);
end

function norm = normalizedCrowding(crowd)
    norm = zeros(numel(crowd),1);
    finite = isfinite(crowd);
    if any(finite)
        maxFinite = max(crowd(finite));
        if maxFinite > 0
            norm(finite) = crowd(finite)/maxFinite;
        end
        norm(~finite) = 1;
    else
        norm(:) = 1;
    end
    norm = min(max(norm,0),1);
end

function count = bitCount(mask)
    mask = uint32(mask);
    count = 0;
    while mask > 0
        count = count + double(bitand(mask,uint32(1)));
        mask = bitshift(mask,-1);
    end
end

function crowd = crowdingDistanceStandalone(Obj)
    n = size(Obj,1);
    crowd = zeros(n,1);
    if n <= 2
        crowd(:) = inf;
        return;
    end
    M = size(Obj,2);
    for m = 1:M
        [vals,order] = sort(Obj(:,m));
        crowd(order(1)) = inf;
        crowd(order(end)) = inf;
        span = vals(end) - vals(1);
        if span <= 0
            continue;
        end
        for j = 2:n-1
            crowd(order(j)) = crowd(order(j)) + (vals(j+1)-vals(j-1))/span;
        end
    end
end

function keys = objectiveKeys(Obj)
    rounded = round(Obj*1e12)/1e12;
    keys = cell(size(rounded,1),1);
    for i = 1:size(rounded,1)
        keys{i} = sprintf('%.12g,',rounded(i,:));
    end
end

function [Population,ids,muF,muCR,recentF,recentCR] = exchangeInformation(Population,ids,muF,muCR,recentF,recentCR,subpops,exchangeMode)
    Obj = Population.objs;
    Con = Population.cons;
    [FrontNo,~] = NDSort(Obj,Con,size(Obj,1));
    CrowdDis = CrowdingDistance(Obj,FrontNo);
    [~,eliteOrder] = sortrows([FrontNo(:),-CrowdDis(:)],[1 2]);
    eliteCount = max(1,ceil(0.05*numel(Population)));
    elites = eliteOrder(1:min(eliteCount,numel(eliteOrder)));

    if strcmpi(exchangeMode,'stable')
        [~,worstOrder] = sortrows([-FrontNo(:),CrowdDis(:)],[1 2]);
        for sid = 1:subpops
            members = find(ids == sid);
            if isempty(members)
                continue;
            end
            worstMembers = worstOrder(ismember(worstOrder,members));
            replaceCount = min(numel(worstMembers),numel(elites));
            for pos = 1:replaceCount
                target = worstMembers(pos);
                source = elites(mod(pos-1,numel(elites))+1);
                if target == source
                    continue;
                end
                Population(target) = Population(source);
                muF(target) = muF(source);
                muCR(target) = muCR(source);
                recentF{target} = recentF{source};
                recentCR{target} = recentCR{source};
                ids(target) = sid;
            end
        end
        return;
    end

    newIDs = initialSubpopIDs(numel(Population),subpops);
    [~,worstOrder] = sortrows([-FrontNo(:),CrowdDis(:)],[1 2]);
    for sid = 1:subpops
        members = find(newIDs == sid);
        if isempty(members)
            continue;
        end
        worstMembers = worstOrder(ismember(worstOrder,members));
        replaceCount = min(numel(worstMembers),numel(elites));
        for pos = 1:replaceCount
            target = worstMembers(pos);
            source = elites(mod(pos-1,numel(elites))+1);
            if target == source
                continue;
            end
            Population(target) = Population(source);
            muF(target) = muF(source);
            muCR(target) = muCR(source);
            recentF{target} = recentF{source};
            recentCR{target} = recentCR{source};
            newIDs(target) = sid;
        end
    end
    ids = newIDs;
end
