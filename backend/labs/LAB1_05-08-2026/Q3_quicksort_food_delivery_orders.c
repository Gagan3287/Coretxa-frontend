#include <stdio.h>

void swap(int *a, int *b)
{
    int temp = *a;
    *a = *b;
    *b = temp;
}

int partition(int arr[], int low, int high)
{
    int pivot = arr[high];
    int i = low - 1;
    int j;

    for (j = low; j < high; j++)
    {
        if (arr[j] < pivot)
        {
            i++;
            swap(&arr[i], &arr[j]);
        }
    }
    swap(&arr[i + 1], &arr[high]);
    return i + 1;
}

void quickSort(int arr[], int low, int high)
{
    if (low < high)
    {
        int pi = partition(arr, low, high);
        quickSort(arr, low, pi - 1);
        quickSort(arr, pi + 1, high);
    }
}

int main()
{
    int orders[100];
    int n, i;

    if (scanf("%d", &n) != 1 || n <= 0 || n > 100)
    {
        printf("Error: Invalid number of elements\n");
        return 1;
    }

    for (i = 0; i < n; i++)
    {
        if (scanf("%d", &orders[i]) != 1)
        {
            printf("Error: Invalid input format\n");
            return 1;
        }
    }

    quickSort(orders, 0, n - 1);

    printf("Sorted Order Amounts:\n");
    for (i = 0; i < n; i++)
    {
        printf("%d ", orders[i]);
    }
    printf("\n");

    return 0;
}
