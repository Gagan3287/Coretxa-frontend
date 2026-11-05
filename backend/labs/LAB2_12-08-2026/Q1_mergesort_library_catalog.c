#include <stdio.h>

void merge(int arr[], int low, int mid, int high)
{
    int n1 = mid - low + 1;
    int n2 = high - mid;
    int left[50], right[50];
    int i, j, k;

    for (i = 0; i < n1; i++)
        left[i] = arr[low + i];
    for (j = 0; j < n2; j++)
        right[j] = arr[mid + 1 + j];

    i = 0;
    j = 0;
    k = low;

    while (i < n1 && j < n2)
    {
        if (left[i] <= right[j])
        {
            arr[k] = left[i];
            i++;
        }
        else
        {
            arr[k] = right[j];
            j++;
        }
        k++;
    }

    while (i < n1)
    {
        arr[k] = left[i];
        i++;
        k++;
    }

    while (j < n2)
    {
        arr[k] = right[j];
        j++;
        k++;
    }
}

void mergeSort(int arr[], int low, int high)
{
    if (low < high)
    {
        int mid = (low + high) / 2;
        mergeSort(arr, low, mid);
        mergeSort(arr, mid + 1, high);
        merge(arr, low, mid, high);
    }
}

int main()
{
    int bookIDs[100];
    int n, i;

    if (scanf("%d", &n) != 1 || n <= 0 || n > 100)
    {
        printf("Error: Invalid number of elements\n");
        return 1;
    }

    for (i = 0; i < n; i++)
    {
        if (scanf("%d", &bookIDs[i]) != 1)
        {
            printf("Error: Invalid input format\n");
            return 1;
        }
    }

    mergeSort(bookIDs, 0, n - 1);

    printf("Sorted Book IDs:\n");
    for (i = 0; i < n; i++)
    {
        printf("%d ", bookIDs[i]);
    }
    printf("\n");

    return 0;
}
