function NSGAII_DebTournament_v290(Global)
% NSGA-II with Deb C-style dual permutations and dominance/crowding tournament.

    Population = Global.Initialization();
    [~,FrontNo,CrowdDis] = EnvironmentalSelection(Population,Global.N);
    while Global.NotTermination(Population)
        MatingPool = TournamentSelectionDiagnostic_v290( ...
            'dual_permutation_dominance',Population,FrontNo,CrowdDis,Global.N);
        Offspring = GA(Population(MatingPool));
        [Population,FrontNo,CrowdDis] = EnvironmentalSelection( ...
            [Population,Offspring],Global.N);
    end
end
