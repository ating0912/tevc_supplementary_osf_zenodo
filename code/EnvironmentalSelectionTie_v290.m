function [Population,FrontNo,CrowdDis] = EnvironmentalSelectionTie_v290(Population,N,mode)
% Native environmental selection with configurable exact crowding ties.

    [FrontNo,MaxFNo]=NDSort(Population.objs,Population.cons,N);
    Next=FrontNo<MaxFNo;
    CrowdDis=CrowdingDistance(Population.objs,FrontNo);
    Last=find(FrontNo==MaxFNo);
    need=N-sum(Next);

    switch mode
        case 'stable'
            keys=[-CrowdDis(Last(:))',(1:numel(Last))'];
        case 'random'
            keys=[-CrowdDis(Last(:))',rand(numel(Last),1)];
        case 'reverse_index'
            keys=[-CrowdDis(Last(:))',-(1:numel(Last))'];
        otherwise
            error('Unknown tie mode: %s',mode);
    end
    [~,order]=sortrows(keys,[1 2]);
    Next(Last(order(1:need)))=true;
    Population=Population(Next);
    FrontNo=FrontNo(Next);
    CrowdDis=CrowdDis(Next);
end
