#include <stdio.h>

int main()
{
    int n, budget, i, w;
    int scholarship[100];
    int merit[100];
    int dp[51][501];

    if (scanf("%d", &n) != 1 || n <= 0 || n > 50)
    {
        printf("Error: Invalid number of students\n");
        return 1;
    }

    scholarship[0] = 0;
    merit[0] = 0;

    for (i = 1; i <= n; i++)
    {
        if (scanf("%d %d", &scholarship[i], &merit[i]) != 2 || scholarship[i] <= 0 || merit[i] <= 0)
        {
            printf("Error: Invalid scholarship cost or merit score for student %d\n", i);
            return 1;
        }
    }

    if (scanf("%d", &budget) != 1 || budget <= 0 || budget > 500)
    {
        printf("Error: Invalid budget\n");
        return 1;
    }

    int capacity = budget;

    for (i = 0; i <= n; i++)
    {
        for (w = 0; w <= capacity; w++)
        {
            dp[i][w] = 0;
        }
    }

    for (i = 1; i <= n; i++)
    {
        for (w = 0; w <= capacity; w++)
        {
            if (scholarship[i] <= w)
            {
                if (merit[i] + dp[i - 1][w - scholarship[i]] > dp[i - 1][w])
                {
                    dp[i][w] = merit[i] + dp[i - 1][w - scholarship[i]];
                }
                else
                {
                    dp[i][w] = dp[i - 1][w];
                }
            }
            else
            {
                dp[i][w] = dp[i - 1][w];
            }
        }
    }

    printf("Selected Students:\n");
    printf("Student\tScholarship\tMerit Score\n");

    w = capacity;
    for (i = n; i >= 1; i--)
    {
        if (dp[i][w] != dp[i - 1][w])
        {
            printf("S%d\t%d\t\t%d\n", i, scholarship[i], merit[i]);
            w = w - scholarship[i];
        }
    }

    printf("\nTotal Scholarship = %d\n", capacity);
    printf("Maximum Total Merit Score = %d\n", dp[n][capacity]);

    return 0;
}
