#include <stdio.h>
#include <string.h>

void solve() {
    long long n, x, s;
    if (scanf("%lld %lld %lld", &n, &x, &s) != 3) return;

    static char u[200005];
    scanf("%s", u);

    long long eia = 0;
    long long rem_I = 0;

    for (long long i = 0; i < n; i++) {
        if (u[i] == 'I') rem_I++;
    }

    long long open_tables = 0;
    long long filler_capacity = 0;

    for (long long i = 0; i < n; i++) {
        char p = u[i];

        if (p == 'I') {
            rem_I--;

            if (open_tables < x) {
                open_tables++;
                filler_capacity += (s - 1);
                eia++;
            }
        }
        else if (p == 'E') {
            if (filler_capacity > 0) {
                filler_capacity--;
                eia++;
            }
        }
        else if (p == 'A') {
            if (open_tables + rem_I < x) {
                open_tables++;
                filler_capacity += (s - 1);
                eia++;
            }
            else if (filler_capacity > 0) {
                filler_capacity--;
                eia++;
            }
            else if (open_tables < x) {
                open_tables++;
                filler_capacity += (s - 1);
                eia++;
            }
        }
    }

    printf("%lld\n", eia);
}

int main() {
    int t;
    if (scanf("%d", &t) != 1) return 0;

    while (t--) {
        solve();
    }

    return 0;
}
