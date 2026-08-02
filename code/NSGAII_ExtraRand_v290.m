function NSGAII_ExtraRand_v290(Global)
% Native NSGA-II with one otherwise unused random draw per generation.

    Population = Global.Initialization();
    [~,FrontNo,CrowdDis] = EnvironmentalSelection(Population,Global.N);
    while Global.NotTermination(Population)
        rand();
        MatingPool = TournamentSelection(2,Global.N,FrontNo,-CrowdDis);
        Offspring = GA(Population(MatingPool));
        [Population,FrontNo,CrowdDis] = EnvironmentalSelection( ...
            [Population,Offspring],Global.N);
    end
end
