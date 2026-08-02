function Offspring = GA_BoundaryDiagnostic_v290(Parent,mode)
% Real-coded v2.9 GA with configurable repair after SBX.

    Parent = Parent.decs;
    Parent1 = Parent(1:floor(end/2),:);
    Parent2 = Parent(floor(end/2)+1:floor(end/2)*2,:);
    [N,D] = size(Parent1);
    Global = GLOBAL.GetObj();
    proC=1; disC=20; proM=1; disM=20;

    beta=zeros(N,D);
    mu=rand(N,D);
    beta(mu<=0.5)=(2*mu(mu<=0.5)).^(1/(disC+1));
    beta(mu>0.5)=(2-2*mu(mu>0.5)).^(-1/(disC+1));
    beta=beta.*(-1).^randi([0,1],N,D);
    beta(rand(N,D)<0.5)=1;
    beta(repmat(rand(N,1)>proC,1,D))=1;
    Offspring=[(Parent1+Parent2)/2+beta.*(Parent1-Parent2)/2
               (Parent1+Parent2)/2-beta.*(Parent1-Parent2)/2];

    Lower=repmat(Global.lower,2*N,1);
    Upper=repmat(Global.upper,2*N,1);
    switch mode
        case 'clip'
            Offspring=min(max(Offspring,Lower),Upper);
        case 'reflect'
            span=Upper-Lower;
            scaled=mod(Offspring-Lower,2*span);
            Offspring=Lower+min(scaled,2*span-scaled);
        case 'random_reset'
            low=Offspring<Lower;
            high=Offspring>Upper;
            outside=low|high;
            replacement=Lower+rand(size(Offspring)).*(Upper-Lower);
            Offspring(outside)=replacement(outside);
        otherwise
            error('Unknown boundary mode: %s',mode);
    end

    Site=rand(2*N,D)<proM/D;
    mu=rand(2*N,D);
    temp=Site & mu<=0.5;
    Offspring(temp)=Offspring(temp)+(Upper(temp)-Lower(temp)).*((2.*mu(temp)+ ...
        (1-2.*mu(temp)).*(1-(Offspring(temp)-Lower(temp))./ ...
        (Upper(temp)-Lower(temp))).^(disM+1)).^(1/(disM+1))-1);
    temp=Site & mu>0.5;
    Offspring(temp)=Offspring(temp)+(Upper(temp)-Lower(temp)).*(1- ...
        (2.*(1-mu(temp))+2.*(mu(temp)-0.5).*(1-(Upper(temp)- ...
        Offspring(temp))./(Upper(temp)-Lower(temp))).^(disM+1)).^(1/(disM+1)));
    Offspring=INDIVIDUAL(Offspring);
end
