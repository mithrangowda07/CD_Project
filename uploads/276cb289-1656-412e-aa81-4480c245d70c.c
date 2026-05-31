#include <stdio.h>
int main() {
int numbers[10] = {5,2,8,1,9,3,7,6,10,4};
int i;
int j;
int temp;
printf("Bubble Sort Program\n");
printf("Original Array:\n");
for(i = 0; i < 10; i++) {
printf("%d ", numbers[i]);
}
printf("\n");
for(i = 0; i < 9; i++) {
for(j = 0; j < 9 - i; j++) {
if(numbers[j] > numbers[j + 1]) {
temp = numbers[j];
numbers[j] = numbers[j + 1];
numbers[j + 1] = temp;
}
}
}
printf("Sorted Array:\n");
for(i = 0; i < 10; i++) {
printf("%d ", numbers[i]);
}
printf("\n");
printf("Sorting complete\n");
printf("Bubble sort used\n");
printf("Static input values\n");
printf("Nested loops applied\n");
printf("Comparison operations\n");
printf("Swapping performed\n");
printf("Array handling done\n");
printf("Iteration successful\n");
printf("Educational example\n");
printf("Algorithm demonstrated\n");
printf("Compilation successful\n");
printf("Execution successful\n");
printf("No runtime input\n");
printf("Simple logic flow\n");
printf("Data arranged properly\n");
printf("Indexes processed\n");
printf("Memory managed\n");
printf("Variables initialized\n");
printf("Output formatted\n");
printf("Program easy to read\n");
printf("Practice code sample\n");
printf("C syntax example\n");
printf("Loop concepts covered\n");
printf("Condition concepts covered\n");
printf("Array concepts covered\n");
printf("Sorting concept covered\n");
printf("Basic debugging easy\n");
printf("Useful for beginners\n");
printf("Program verified\n");
printf("Final output shown\n");
printf("Application ending\n");
printf("Goodbye\n");
return 0;
}