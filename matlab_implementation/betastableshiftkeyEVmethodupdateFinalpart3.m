%%% BER vs Betazero=-betaone as function of L =[2....... 500]
%%% with & without AWGN noise considered


clc
clear


alphazero = 1.5;
alphaone =  1.5;
Numbersofbitssent = 1000;
numbersofnoisesamplesperbit = 1000;
beta = 0.1:0.1:1;
[r,c] = size (beta);
betazero= -beta;
betaone=  beta;
sequencelengthafterpartition = [2 4 5 8 10 20 25 40 50 100 200 250 500];
[Lr,Lc]= size(sequencelengthafterpartition);

for se= 1:Lc
    
    
    
for f=1:c

betazero= -beta(1,f);
betaone=  beta(1,f);
%%%%%%%% Transmitter %%%%%%%%%

T = [1:1:Numbersofbitssent*numbersofnoisesamplesperbit];
T =vec2mat(T,1);
B = binornd(1,0.5,1,Numbersofbitssent); %%Benouli Binary random Number Generator
B =vec2mat(B,1);

for i=1:Numbersofbitssent
  if B(i,1)==0;

        if i==1
x = stblrnd(alphazero,betazero,1,0,numbersofnoisesamplesperbit,1);
T(i:numbersofnoisesamplesperbit) = x;
        end
  else
 x = stblrnd(alphazero,betazero,1,0,numbersofnoisesamplesperbit,1);       
    T(((i-1)*numbersofnoisesamplesperbit)+1:i*numbersofnoisesamplesperbit) = x; 
        
  end

  if B(i,1)==1;
    
    if i==1
x = stblrnd(alphaone,betaone,1,0,numbersofnoisesamplesperbit,1);
T(i:numbersofnoisesamplesperbit) = x;
    end
  else
 x = stblrnd(alphaone,betaone,1,0,numbersofnoisesamplesperbit,1);       
    T(((i-1)*numbersofnoisesamplesperbit)+1:i*numbersofnoisesamplesperbit) = x;
    
  end
   
end

% figure;
% subplot(211)
% stem(B);
% ylabel('B[t]');
% xlabel('t');
% title('Binary Information sequence -- TB[t] vs. t');
% 
% subplot(212)
% plot(T);
% ylabel('T(t)');
% xlabel('t');
% title('Transmitted Noise sequence -- TN(t) vs. t');

%%%%%%%% Data centerization

% Transform = [1:1:3000];
% Transform = Transform-Transform;
% Transform = vec2mat(Transform,1);
% Transform(1:1000,1) = T(1:1000,1);
% 
% 
% for z=1:1:1000
% T(z,1)= Transform(3*z,1) + Transform(3*z-1,1) - (2*(Tansform(3*z-2,1)))  ;
% 
% end

%%%%%% Channel %%%%%%

T = awgn(T,10,'measured');

%%%%%%%% xxxxxxxx %%%%%%%%%%






%%%%%%%% Estimator at Receiver %%%%%%%
[lengthoftransmittedsequence,columns] = size (T);
N = (lengthoftransmittedsequence/Numbersofbitssent);
L = sequencelengthafterpartition(1,se); %%number of segments
K  =  N/L;

Estimatedalphas = [1:1:Numbersofbitssent];
Estimatedalphas = vec2mat(Estimatedalphas,1);

Estimatedbetas  = [1:1:Numbersofbitssent];
Estimatedbetas = vec2mat(Estimatedbetas,1);

for v= 1:Numbersofbitssent

%% for estimation one bit from transmitted bits
                     %segmentmaximum(1,1) = log(max(T(1:K,1)));            %% log(max(  T   (((v-1)*K)+1):K*v,1)));
                      %segmentminimum(1,1) = log(min(T(1:K,1)));

for j=1:L

segmentmaximum(j,1) = log( max(    T (   ((((j-1)*K)+1) + ((v-1)*N))      : ((j*K)+ ((v-1)*N))  )        ));  %% T(((j-1)*K)+1:j*K)      T (   ((((j-1)*K*)+1) + ((v-1)*N))      : ((j*K)+ ((v-1)*N))  ) 
segmentminimum(j,1) = log(-min(    T (   ((((j-1)*K)+1) + ((v-1)*N))      : ((j*K)+ ((v-1)*N))  )        ));

end

Summationmaximum = sum (segmentmaximum);  
Summationminimum = sum (segmentminimum);

Samplemeanmaximum = (Summationmaximum/L);    %% sample mean of maximum
Samplemeanminimum = (Summationminimum/L);    %% sample mean  of minimum


varianceofmaximum =  (     (sum  ((segmentmaximum-Samplemeanmaximum).^2)) /   (1/(L-1))  ) ;   %% variance  of maximum
varianceofminimum =  (     (sum  ((segmentminimum-Samplemeanminimum).^2)) /   (1/(L-1))  ) ;   %% variance  of minimum

standarddeviationofmaximum = sqrt(varianceofmaximum); %% standard deviation of maximum
standarddeviationofminimum = sqrt(varianceofminimum); %% standard deviation of minimum


Estimatedalphas(v,1) = (  (pi/4.8890)     *    ((1/standarddeviationofmaximum)+(1/standarddeviationofminimum))   );
Estimatedbetas(v,1)  = - (1-   (2 /   ( 1+    exp( (Estimatedalphas(v,1)) *  (Samplemeanmaximum - Samplemeanminimum)  ))));  
end



%%%%%% Decision and BER %%%%%%%

threshold = ((betazero + betaone) / 2);
for w=1:Numbersofbitssent
    
  
    if Estimatedbetas(w,1)>= threshold;

   receiveddata(w,1) = 1
   
    else
        
    receiveddata(w,1) = 0
    
    end
end

bitsinerror = 0;
for ww = 1:Numbersofbitssent
    
     if receiveddata(ww)~= B(ww)
         
         bitsinerror = bitsinerror + 1;
         
     end
end
BER(f,se) = (bitsinerror/Numbersofbitssent);

% figure;
% subplot(211)
% plot(T);
% ylabel('RB(t)');
% xlabel('t');
% title('Received Nosie sequence -- RN(t) vs. t');
% 
% 
% subplot(212)
% stem(receiveddata);
% ylabel('Received R[t]');
% xlabel('t');
% title('Recovered Binary sequence -- RB[t] vs. t');

% 
% semilogy(beta(1,f),BER,'b.--');
% hold on;
% % legend('ALPHA 0.1','ALPHA 0.3','ALPHA 0.5','ALPHA 0.7','ALPHA 0.9','ALPHA 1.1','ALPHA 1.3','ALPHA 1.5','ALPHA 1.7','ALPHA 1.9');
% xlabel('Values of Beta  (where beta for one= - beta for zero')
% ylabel('Bit Error Rate')
% title('BER vs BETA')


end



end
BERL1= BER(1:10,1);
BERL2= BER(1:10,2);
BERL3= BER(1:10,3);
BERL4= BER(1:10,4);
BERL5= BER(1:10,5);
BERL6= BER(1:10,6);
BERL7= BER(1:10,7);
BERL8= BER(1:10,8);
BERL9= BER(1:10,9);
BERL10= BER(1:10,10);
BERL11= BER(1:10,11);
BERL12= BER(1:10,12);
BERL13= BER(1:10,13);
beta = vec2mat(beta,1);

figure;
semilogy(beta,[BERL1 BERL2 BERL3 BERL4 BERL5 BERL6 BERL7 BERL8 BERL9 BERL10 BERL11 BERL12 BERL13],'g*--');
axis([0.1 1 0.0001 1]) 
hold on;
legend('L=2 K=500','L=4 K=250','L=5 K=200','L=8 K=125','L=10 K=100','L=20 K=50','L=25 K=40','L=40 K=50','L=50 K=20','L=100 K=10','L=200 K=5','L=250 K=4','L=500 K=2');
ylabel('Bit Error Rate')
xlabel('Beta  (beta for message 1 = - beta for message 0')
title('BER vs BETA with K=[2 4 5 8 10 20 25 40 50 100 200 250 500] in AWGN noise')

