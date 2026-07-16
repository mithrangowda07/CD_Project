#include <stdio.h>

int main() {
    int n = 15;
    long long fib[20];
    int i;
    long long sum = 0;

    printf("Fibonacci Sequence Program\n");
    printf("Generating first %d terms:\n", n);

    fib[0] = 0;
    fib[1] = 1;

    printf("%lld ", fib[0]);
    printf("%lld ", fib[1]);
    sum = fib[0] + fib[1];

    for(i = 2; i < n; i++) {
        fib[i] = fib[i - 1] + fib[i - 2];
        printf("%lld ", fib[i]);
        sum += fib[i];
    }

    printf("\n");
    printf("Sum of first %d terms = %lld\n", n, sum);
    printf("Fibonacci calculation complete\n");

    return 0;
}
