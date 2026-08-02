function NSGAII_CrowdingTie_v290(Global,mode)
% NSGA-II with configurable environmental-selection crowding ties.

    Population=Global.Initialization();
    [~,FrontNo,CrowdDis]=EnvironmentalSelectionTie_v290(Population,Global.N,mode);
    while Global.NotTermination(Population)
        MatingPool=TournamentSelection(2,Global.N,FrontNo,-CrowdDis);
        Offspring=GA(Population(MatingPool));
        [Population,FrontNo,CrowdDis]=EnvironmentalSelectionTie_v290( ...
            [Population,Offspring],Global.N,mode);
    end
end
