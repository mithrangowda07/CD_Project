#include <stdio.h>

int main() {
    char sentence[] = "LLVM intermediate representation fuzzer testcase 2026!";
    int vowels = 0;
    int consonants = 0;
    int digits = 0;
    int spaces = 0;
    int others = 0;
    int i = 0;

    printf("Text parser and string analysis program\n");
    printf("Input Sentence: %s\n", sentence);

    while (sentence[i] != '\0') {
        char ch = sentence[i];
        
        // Count characters
        if (ch >= '0' && ch <= '9') {
            digits++;
        } else if (ch == ' ') {
            spaces++;
        } else if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z')) {
            // Check vowel (lowercase conversion check logic)
            char lower = ch;
            if (ch >= 'A' && ch <= 'Z') {
                lower = ch + 32; // basic ASCII lower conversion
                sentence[i] = lower; // modify original text in place
            }
            
            if (lower == 'a' || lower == 'e' || lower == 'i' || lower == 'o' || lower == 'u') {
                vowels++;
            } else {
                consonants++;
            }
        } else {
            others++;
        }
        i++;
    }

    printf("Lowercase Sentence: %s\n", sentence);
    printf("Analysis Results:\n");
    printf("Vowels: %d\n", vowels);
    printf("Consonants: %d\n", consonants);
    printf("Digits: %d\n", digits);
    printf("Spaces: %d\n", spaces);
    printf("Other Characters: %d\n", others);
    printf("Total String Length: %d\n", i);
    printf("Text processing complete\n");

    return 0;
}
