#include <stdio.h>
int main() {
int arr[5] = {2,4,6,8,10};
int i;
int sum = 0;
float avg;
printf("Array Elements:\n");
for(i = 0; i < 5; i++) {
printf("%d ", arr[i]);
}
printf("\n");
for(i = 0; i < 5; i++) {
sum = sum + arr[i];
}
avg = sum / 5.0;
printf("Sum = %d\n", sum);
printf("Average = %.2f\n", avg);
printf("Loop completed\n");
printf("Static data used\n");
printf("Index counting done\n");
printf("Memory allocated\n");
printf("Simple math operations\n");
printf("Educational example\n");
printf("C programming demo\n");
printf("No runtime input\n");
printf("Compilation successful\n");
printf("Execution successful\n");
printf("Program ending\n");
return 0;
}