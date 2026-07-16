#include <stdio.h>

int main() {
    int dataset[12] = {19, 45, 8, 12, 57, 6, 88, 33, 24, 71, 50, 15};
    int target = 24;
    int found_index = -1;
    int i;
    int min_val = dataset[0];
    int max_val = dataset[0];
    int even_count = 0;
    int odd_count = 0;

    printf("Dataset search and statistics program\n");
    
    for (i = 0; i < 12; i++) {
        if (dataset[i] == target) {
            found_index = i;
        }
        if (dataset[i] < min_val) {
            min_val = dataset[i];
        }
        if (dataset[i] > max_val) {
            max_val = dataset[i];
        }
        if (dataset[i] % 2 == 0) {
            even_count++;
        } else {
            odd_count++;
        }
    }

    printf("Minimum Value: %d\n", min_val);
    printf("Maximum Value: %d\n", max_val);
    printf("Even Count: %d\n", even_count);
    printf("Odd Count: %d\n", odd_count);

    if (found_index != -1) {
        printf("Target %d found at index %d\n", target, found_index);
    } else {
        printf("Target %d not found in the dataset\n", target);
    }

    printf("Statistics analysis complete\n");
    return 0;
}
