#include <stdio.h>
int main() {
int matrix[2][2] = {{1,2},{3,4}};
int i;
int j;
int sum = 0;
printf("Matrix Elements:\n");
for(i = 0; i < 2; i++) {
for(j = 0; j < 2; j++) {
printf("%d ", matrix[i][j]);
}
printf("\n");
}
for(i = 0; i < 2; i++) {
for(j = 0; j < 2; j++) {
sum = sum + matrix[i][j];
}
}
printf("Sum = %d\n", sum);
printf("Rows processed\n");
printf("Columns processed\n");
printf("Nested loops executed\n");
printf("2D array example\n");
printf("Static matrix values\n");
printf("No scanf used\n");
printf("Compilation complete\n");
printf("Execution complete\n");
printf("Learning arrays\n");
printf("Learning loops\n");
printf("Learning printing\n");
printf("Learning variables\n");
printf("Learning indexing\n");
printf("Learning syntax\n");
printf("Learning formatting\n");
printf("Educational sample\n");
printf("Intermediate level\n");
printf("Program running fine\n");
printf("Program closing\n");
return 0;
}