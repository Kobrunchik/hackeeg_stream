clear;
clc;

%x=readmatrix('PdataDenHide2.txt');
%x1=readmatrix('DataSPIHide2.txt');
x=readmatrix('PdataDen4.txt');
x1=readmatrix('DataSPIDen4.txt');

%x=readmatrix('PdataNoc3.txt');
%x1=readmatrix('DataSPINoc3.txt');

Y = x(:, 1);
Y=Y*5.364418*10^(-7);

N = size(Y,1);
Fs = x(N, 1);
Y([N, N-1, N-2], :)=[];
N = size(Y,1);

dt = 1/Fs;
t = dt*(0:N-1)';
N1 = size(x1,1);
t1 = x1(:, 1);
for i=2:(N1)
   t1(i)=t1(i-1)+t1(i); 
end

figure;
plot(t,Y);
figure;
plot(t1,x1);
