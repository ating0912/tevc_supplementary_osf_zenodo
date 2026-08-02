function NSGAII_RandomTie_v290(Global)
% NSGA-II with replacement and random resolution of exact tournament ties.

    Population = Global.Initialization();
    [~,FrontNo,CrowdDis] = EnvironmentalSelectionNSGAII_v290( ...
        Population,Global.N);
    while Global.NotTermination(Population)
        MatingPool = TournamentSelectionDiagnostic_v290( ...
            'with_replacement_random_tie',Population,FrontNo,CrowdDis,Global.N);
        Offspring = GA(Population(MatingPool));
        [Population,FrontNo,CrowdDis] = EnvironmentalSelectionNSGAII_v290( ...
            [Population,Offspring],Global.N);
    end
end
