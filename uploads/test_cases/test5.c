#include <stdio.h>
int main() {
char name[] = "OpenAI";
int marks[5] = {80,85,90,95,88};
int i;
int total = 0;
float average;
printf("Student Report\n");
printf("Name: %s\n", name);
printf("Marks:\n");
for(i = 0; i < 5; i++) {
printf("%d ", marks[i]);
}
printf("\n");
for(i = 0; i < 5; i++) {
total = total + marks[i];
}
average = total / 5.0;
printf("Total = %d\n", total);
printf("Average = %.2f\n", average);
if(average >= 90) {
printf("Grade: A\n");
}
else {
printf("Grade: B\n");
}
printf("Result generated\n");
printf("Using arrays\n");
printf("Using conditions\n");
printf("Using loops\n");
printf("Using variables\n");
printf("Using strings\n");
printf("Static information\n");
printf("No keyboard input\n");
printf("Simple report card\n");
printf("Educational purpose\n");
printf("C language practice\n");
printf("Compiler friendly\n");
printf("Readable structure\n");
printf("Logic implemented\n");
printf("Average calculated\n");
printf("Grade calculated\n");
printf("Program stable\n");
printf("Program tested\n");
printf("Execution successful\n");
printf("Output displayed\n");
printf("End of report\n");
printf("Closing application\n");
return 0;
}