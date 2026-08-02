function Offspring = GA_DebBounded_v290(Parent,mutationMode)
% Deb C bounded SBX with selectable polynomial-mutation implementation.

    Parent = Parent.decs;
    Parent1 = Parent(1:floor(end/2),:);
    Parent2 = Parent(floor(end/2)+1:floor(end/2)*2,:);
    [N,D] = size(Parent1);
    Global = GLOBAL.GetObj();
    proC = 1;
    disC = 20;
    proM = 1;
    disM = 20;
    lower = Global.lower;
    upper = Global.upper;

    Child1 = Parent1;
    Child2 = Parent2;
    for i = 1:N
        if rand <= proC
            for j = 1:D
                if rand <= 0.5 && abs(Parent1(i,j)-Parent2(i,j)) > 1e-14
                    y1 = min(Parent1(i,j),Parent2(i,j));
                    y2 = max(Parent1(i,j),Parent2(i,j));
                    yl = lower(j);
                    yu = upper(j);
                    r = rand;

                    beta = 1 + 2*(y1-yl)/(y2-y1);
                    alpha = 2-beta^(-(disC+1));
                    if r <= 1/alpha
                        betaq = (r*alpha)^(1/(disC+1));
                    else
                        betaq = (1/(2-r*alpha))^(1/(disC+1));
                    end
                    c1 = 0.5*((y1+y2)-betaq*(y2-y1));

                    beta = 1 + 2*(yu-y2)/(y2-y1);
                    alpha = 2-beta^(-(disC+1));
                    if r <= 1/alpha
                        betaq = (r*alpha)^(1/(disC+1));
                    else
                        betaq = (1/(2-r*alpha))^(1/(disC+1));
                    end
                    c2 = 0.5*((y1+y2)+betaq*(y2-y1));

                    c1 = min(max(c1,yl),yu);
                    c2 = min(max(c2,yl),yu);
                    if rand <= 0.5
                        Child1(i,j) = c2;
                        Child2(i,j) = c1;
                    else
                        Child1(i,j) = c1;
                        Child2(i,j) = c2;
                    end
                end
            end
        end
    end
    Offspring = [Child1;Child2];

    switch mutationMode
        case 'platemo'
            Lower = repmat(lower,2*N,1);
            Upper = repmat(upper,2*N,1);
            Site = rand(2*N,D) < proM/D;
            mu = rand(2*N,D);
            temp = Site & mu <= 0.5;
            Offspring(temp) = Offspring(temp)+(Upper(temp)-Lower(temp)).* ...
                ((2.*mu(temp)+(1-2.*mu(temp)).* ...
                (1-(Offspring(temp)-Lower(temp))./(Upper(temp)-Lower(temp))).^ ...
                (disM+1)).^(1/(disM+1))-1);
            temp = Site & mu > 0.5;
            Offspring(temp) = Offspring(temp)+(Upper(temp)-Lower(temp)).* ...
                (1-(2.*(1-mu(temp))+2.*(mu(temp)-0.5).* ...
                (1-(Upper(temp)-Offspring(temp))./(Upper(temp)-Lower(temp))).^ ...
                (disM+1)).^(1/(disM+1)));
        case 'deb_sequential'
            for i = 1:2*N
                for j = 1:D
                    if rand <= proM/D
                        y = Offspring(i,j);
                        yl = lower(j);
                        yu = upper(j);
                        delta1 = (y-yl)/(yu-yl);
                        delta2 = (yu-y)/(yu-yl);
                        r = rand;
                        if r <= 0.5
                            xy = 1-delta1;
                            val = 2*r+(1-2*r)*xy^(disM+1);
                            deltaq = val^(1/(disM+1))-1;
                        else
                            xy = 1-delta2;
                            val = 2*(1-r)+2*(r-0.5)*xy^(disM+1);
                            deltaq = 1-val^(1/(disM+1));
                        end
                        Offspring(i,j) = min(max(y+deltaq*(yu-yl),yl),yu);
                    end
                end
            end
        otherwise
            error('Unknown mutation mode: %s',mutationMode);
    end
    Offspring = INDIVIDUAL(Offspring);
end
