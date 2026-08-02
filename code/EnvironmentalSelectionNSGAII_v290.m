function [Population,FrontNo,CrowdDis] = EnvironmentalSelectionNSGAII_v290(Population,N)
% Path-independent copy of PlatEMO v2.9 NSGA-II environmental selection.

    [FrontNo,MaxFNo] = NDSort(Population.objs,Population.cons,N);
    Next = FrontNo < MaxFNo;
    CrowdDis = CrowdingDistance(Population.objs,FrontNo);
    Last = find(FrontNo==MaxFNo);
    [~,Rank] = sort(CrowdDis(Last),'descend');
    Next(Last(Rank(1:N-sum(Next)))) = true;
    Population = Population(Next);
    FrontNo = FrontNo(Next);
    CrowdDis = CrowdDis(Next);
end
