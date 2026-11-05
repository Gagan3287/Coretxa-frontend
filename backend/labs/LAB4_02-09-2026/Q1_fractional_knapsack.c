#include <stdio.h>

struct Item
{
    char name[10];
    int weight;
    int profit;
    double ratio;
};

int main()
{
    int n, capacity, i, j;
    struct Item items[100];
    struct Item temp;
    double totalProfit = 0.0;

    if (scanf("%d", &n) != 1 || n <= 0 || n > 100)
    {
        printf("Error: Invalid number of items\n");
        return 1;
    }

    for (i = 0; i < n; i++)
    {
        snprintf(items[i].name, sizeof(items[i].name), "I%d", i + 1);
        if (scanf("%d %d", &items[i].weight, &items[i].profit) != 2 || items[i].weight <= 0)
        {
            printf("Error: Invalid weight or profit for item %d\n", i + 1);
            return 1;
        }
        items[i].ratio = 0;
    }

    if (scanf("%d", &capacity) != 1 || capacity <= 0)
    {
        printf("Error: Invalid capacity\n");
        return 1;
    }

    int remaining = capacity;

    for (i = 0; i < n; i++)
    {
        items[i].ratio = (double)items[i].profit / items[i].weight;
    }

    for (i = 0; i < n - 1; i++)
    {
        for (j = i + 1; j < n; j++)
        {
            if (items[j].ratio > items[i].ratio)
            {
                temp = items[i];
                items[i] = items[j];
                items[j] = temp;
            }
        }
    }

    printf("Items sorted by Profit/Weight ratio:\n");
    for (i = 0; i < n; i++)
    {
        printf("%s Weight=%d Profit=%d Ratio=%.2f\n",
               items[i].name, items[i].weight, items[i].profit, items[i].ratio);
    }

    printf("\nSelection Steps:\n");
    for (i = 0; i < n && remaining > 0; i++)
    {
        if (items[i].weight <= remaining)
        {
            remaining -= items[i].weight;
            totalProfit += items[i].profit;
            printf("Selected full %s -> Weight=%d Profit=%d Remaining Capacity=%d\n",
                   items[i].name, items[i].weight, items[i].profit, remaining);
        }
        else
        {
            double fraction = (double)remaining / items[i].weight;
            double fractionProfit = items[i].profit * fraction;
            totalProfit += fractionProfit;
            printf("Selected %.2f fraction of %s -> Profit=%.2f Remaining Capacity=0\n",
                   fraction, items[i].name, fractionProfit);
            remaining = 0;
        }
    }

    printf("\nMaximum Total Profit = %.2f\n", totalProfit);

    return 0;
}
