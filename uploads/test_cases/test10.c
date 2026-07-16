#include <stdio.h>

int main() {
    int mat1[3][2] = {
        {1, 2},
        {3, 4},
        {5, 6}
    };
    int mat2[2][3] = {
        {7, 8, 9},
        {10, 11, 12}
    };
    int result[3][3] = {0};
    int i, j, k;

    printf("Matrix Multiplication Program\n");
    printf("Matrix 1 (3x2):\n");
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 2; j++) {
            printf("%d ", mat1[i][j]);
        }
        printf("\n");
    }

    printf("Matrix 2 (2x3):\n");
    for (i = 0; i < 2; i++) {
        for (j = 0; j < 3; j++) {
            printf("%d ", mat2[i][j]);
        }
        printf("\n");
    }

    // Multiplication logic
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) {
            for (k = 0; k < 2; k++) {
                result[i][j] += mat1[i][k] * mat2[k][j];
            }
        }
    }

    printf("Result Matrix (3x3):\n");
    for (i = 0; i < 3; i++) {
        for (j = 0; j < 3; j++) {
            printf("%d ", result[i][j]);
        }
        printf("\n");
    }

    printf("Computation finished successfully\n");
    printf("Matrix calculations complete\n");

    return 0;
}
