function NSGAII_SamplingDiagnostic_v290(Global)
% Native v2.9 NSGA-II with objective snapshots around environmental selection.

    global NSGAII_SAMPLING_TRACE
    NSGAII_SAMPLING_TRACE = struct('previous',[],'offspring',[],'mixed',[], ...
        'final',[],'archive',[]);

    Population = Global.Initialization();
    [~,FrontNo,CrowdDis] = EnvironmentalSelection(Population,Global.N);
    archiveObj = Population.objs;

    while Global.NotTermination(Population)
        previous = Population;
        MatingPool = TournamentSelection(2,Global.N,FrontNo,-CrowdDis);
        Offspring = GA(Population(MatingPool));
        mixed = [Population,Offspring];
        [Population,FrontNo,CrowdDis] = EnvironmentalSelection(mixed,Global.N);
        archiveObj = nondominatedObjectives([archiveObj;Offspring.objs]);

        NSGAII_SAMPLING_TRACE.previous = previous;
        NSGAII_SAMPLING_TRACE.offspring = Offspring;
        NSGAII_SAMPLING_TRACE.mixed = mixed;
        NSGAII_SAMPLING_TRACE.final = Population;
        NSGAII_SAMPLING_TRACE.archive = archiveObj;
    end
end

function Obj = nondominatedObjectives(Obj)
    Obj = unique(Obj,'rows');
    Obj = Obj(NDSort(Obj,1)==1,:);
end
