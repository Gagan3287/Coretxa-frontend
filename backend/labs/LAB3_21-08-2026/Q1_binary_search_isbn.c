#include <stdio.h>

int iterativeBinarySearch(int arr[], int n, int key, int *comparisons)
{
    int low = 0;
    int high = n - 1;
    *comparisons = 0;

    while (low <= high)
    {
        int mid = (low + high) / 2;
        (*comparisons)++;

        if (arr[mid] == key)
        {
            return mid;
        }
        else if (arr[mid] < key)
        {
            low = mid + 1;
        }
        else
        {
            high = mid - 1;
        }
    }
    return -1;
}

int recursiveBinarySearch(int arr[], int low, int high, int key, int *comparisons)
{
    if (low > high)
    {
        return -1;
    }

    int mid = (low + high) / 2;
    (*comparisons)++;

    if (arr[mid] == key)
    {
        return mid;
    }
    else if (arr[mid] < key)
    {
        return recursiveBinarySearch(arr, mid + 1, high, key, comparisons);
    }
    else
    {
        return recursiveBinarySearch(arr, low, mid - 1, key, comparisons);
    }
}

void sortArray(int arr[], int n)
{
    int i, j, temp;
    for (i = 0; i < n - 1; i++)
    {
        for (j = 0; j < n - i - 1; j++)
        {
            if (arr[j] > arr[j + 1])
            {
                temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

int main()
{
    int isbn[100];
    int n, key, i;
    int result1, result2;
    int comparisons1 = 0, comparisons2 = 0;

    if (scanf("%d", &n) != 1 || n <= 0 || n > 100)
    {
        printf("Error: Invalid number of elements\n");
        return 1;
    }

    for (i = 0; i < n; i++)
    {
        if (scanf("%d", &isbn[i]) != 1)
        {
            printf("Error: Invalid input format\n");
            return 1;
        }
    }

    if (scanf("%d", &key) != 1)
    {
        printf("Error: Invalid search key\n");
        return 1;
    }

    sortArray(isbn, n);

    printf("Sorted ISBN Catalog:\n");
    for (i = 0; i < n; i++)
    {
        printf("%d ", isbn[i]);
    }
    printf("\n\n");

    result1 = iterativeBinarySearch(isbn, n, key, &comparisons1);

    comparisons2 = 0;
    result2 = recursiveBinarySearch(isbn, 0, n - 1, key, &comparisons2);

    printf("ITERATIVE BINARY SEARCH\n");
    if (result1 != -1)
    {
        printf("ISBN %d found at index %d\n", key, result1);
    }
    else
    {
        printf("ISBN %d not found\n", key);
    }
    printf("Number of comparisons = %d\n\n", comparisons1);

    printf("RECURSIVE BINARY SEARCH\n");
    if (result2 != -1)
    {
        printf("ISBN %d found at index %d\n", key, result2);
    }
    else
    {
        printf("ISBN %d not found\n", key);
    }
    printf("Number of comparisons = %d\n", comparisons2);

    return 0;
}
