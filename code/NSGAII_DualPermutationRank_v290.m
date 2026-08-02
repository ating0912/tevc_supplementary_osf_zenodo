function NSGAII_DualPermutationRank_v290(Global)
% NSGA-II with Deb-style dual permutations and rank/crowding comparison.

    Population = Global.Initialization();
    [~,FrontNo,CrowdDis] = EnvironmentalSelectionNSGAII_v290( ...
        Population,Global.N);
    while Global.NotTermination(Population)
        MatingPool = TournamentSelectionDiagnostic_v290( ...
            'dual_permutation_rank',Population,FrontNo,CrowdDis,Global.N);
        Offspring = GA(Population(MatingPool));
        [Population,FrontNo,CrowdDis] = EnvironmentalSelectionNSGAII_v290( ...
            [Population,Offspring],Global.N);
    end
end
