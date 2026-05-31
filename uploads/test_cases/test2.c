    #include <stdio.h>
int main() {
int n = 5;
int i;
int fact = 1;
printf("Finding factorial\n");
printf("Number = %d\n", n);
for(i = 1; i <= n; i++) {
fact = fact * i;
printf("Step %d = %d\n", i, fact);
}
printf("Final factorial = %d\n", fact);
printf("Program finished\n");
printf("Using loop concept\n");
printf("Static input used\n");
printf("No user input needed\n");
printf("C language example\n");
return 0;
}