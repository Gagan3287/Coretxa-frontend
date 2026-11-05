#include <stdio.h>
#include <limits.h>

int m[100][100];
int s[100][100];

void printParenthesis(int i, int j)
{
    if (i == j)
    {
        printf("A%d", i);
        return;
    }

    printf("(");
    printParenthesis(i, s[i][j]);
    printf(" x ");
    printParenthesis(s[i][j] + 1, j);
    printf(")");
}

int main()
{
    int n, i, j, k, L;
    int p[100];

    if (scanf("%d", &n) != 1 || n <= 0 || n > 50)
    {
        printf("Error: Invalid number of matrices\n");
        return 1;
    }

    for (i = 0; i <= n; i++)
    {
        if (scanf("%d", &p[i]) != 1 || p[i] <= 0)
        {
            printf("Error: Invalid matrix dimension p[%d]\n", i);
            return 1;
        }
    }

    for (i = 1; i <= n; i++)
    {
        m[i][i] = 0;
    }

    for (L = 2; L <= n; L++)
    {
        for (i = 1; i <= n - L + 1; i++)
        {
            j = i + L - 1;
            m[i][j] = INT_MAX;

            for (k = i; k < j; k++)
            {
                int cost = m[i][k] + m[k + 1][j] + p[i - 1] * p[k] * p[j];
                if (cost < m[i][j])
                {
                    m[i][j] = cost;
                    s[i][j] = k;
                }
            }
        }
    }

    printf("Optimal Parenthesization:\n");
    printParenthesis(1, n);
    printf("\n\nMinimum number of scalar multiplications = %d\n", m[1][n]);

    return 0;
}
