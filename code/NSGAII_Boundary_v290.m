function NSGAII_Boundary_v290(Global,mode)
% NSGA-II using a selected SBX boundary-repair policy.

    Population=Global.Initialization();
    [~,FrontNo,CrowdDis]=EnvironmentalSelection(Population,Global.N);
    while Global.NotTermination(Population)
        MatingPool=TournamentSelection(2,Global.N,FrontNo,-CrowdDis);
        Offspring=GA_BoundaryDiagnostic_v290(Population(MatingPool),mode);
        [Population,FrontNo,CrowdDis]=EnvironmentalSelection( ...
            [Population,Offspring],Global.N);
    end
end
