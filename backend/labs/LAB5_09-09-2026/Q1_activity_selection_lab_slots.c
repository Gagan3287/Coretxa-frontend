#include <stdio.h>

struct Activity
{
    char name[10];
    int start;
    int finish;
};

int main()
{
    int n, i, j;
    struct Activity a[100];
    struct Activity temp;

    if (scanf("%d", &n) != 1 || n <= 0 || n > 100)
    {
        printf("Error: Invalid number of groups\n");
        return 1;
    }

    for (i = 0; i < n; i++)
    {
        snprintf(a[i].name, sizeof(a[i].name), "G%d", i + 1);
        if (scanf("%d %d", &a[i].start, &a[i].finish) != 2 || a[i].start < 0 || a[i].finish < a[i].start)
        {
            printf("Error: Invalid start or finish time for group %d\n", i + 1);
            return 1;
        }
    }

    for (i = 0; i < n - 1; i++)
    {
        for (j = i + 1; j < n; j++)
        {
            if (a[i].finish > a[j].finish)
            {
                temp = a[i];
                a[i] = a[j];
                a[j] = temp;
            }
        }
    }

    printf("Activities sorted by finish time:\n");
    for (i = 0; i < n; i++)
    {
        printf("%s %d %d\n", a[i].name, a[i].start, a[i].finish);
    }

    printf("\nSelected Groups:\n");

    int lastFinish = a[0].finish;
    printf("%s %d %d\n", a[0].name, a[0].start, a[0].finish);
    int count = 1;

    for (i = 1; i < n; i++)
    {
        if (a[i].start >= lastFinish)
        {
            printf("%s %d %d\n", a[i].name, a[i].start, a[i].finish);
            lastFinish = a[i].finish;
            count++;
        }
    }

    printf("\nMaximum number of groups = %d\n", count);

    return 0;
}
