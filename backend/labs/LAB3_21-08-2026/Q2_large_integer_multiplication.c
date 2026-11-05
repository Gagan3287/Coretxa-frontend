#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define MAX 1000

void padLeft(char *dest, const char *src, int totalLen)
{
    int srcLen = strlen(src);
    int padLen = totalLen - srcLen;
    int i;

    for (i = 0; i < padLen; i++)
    {
        dest[i] = '0';
    }
    for (i = 0; i < srcLen; i++)
    {
        dest[padLen + i] = src[i];
    }
    dest[totalLen] = '\0';
}

void removeLeadingZeros(char *str)
{
    int i = 0;
    int len = strlen(str);

    while (str[i] == '0' && i < len - 1)
    {
        i++;
    }

    if (i > 0)
    {
        memmove(str, str + i, len - i + 1);
    }
}

void addStrings(const char *x, const char *y, char *result)
{
    int lenX = strlen(x);
    int lenY = strlen(y);
    int maxLen = (lenX > lenY) ? lenX : lenY;
    char a[MAX], b[MAX];
    int carry = 0;
    int i;
    char temp[MAX];
    int pos = 0;

    padLeft(a, x, maxLen);
    padLeft(b, y, maxLen);

    for (i = maxLen - 1; i >= 0; i--)
    {
        int digitA = a[i] - '0';
        int digitB = b[i] - '0';
        int sum = digitA + digitB + carry;
        carry = sum / 10;
        temp[pos] = (char)((sum % 10) + '0');
        pos++;
    }

    if (carry > 0)
    {
        temp[pos] = (char)(carry + '0');
        pos++;
    }

    for (i = 0; i < pos; i++)
    {
        result[i] = temp[pos - 1 - i];
    }
    result[pos] = '\0';

    removeLeadingZeros(result);
}

void multiply(const char *x, const char *y, char *result)
{
    int lenX = strlen(x);
    int lenY = strlen(y);
    int n = (lenX > lenY) ? lenX : lenY;

    if (n == 1)
    {
        int product = (x[0] - '0') * (y[0] - '0');
        sprintf(result, "%d", product);
        return;
    }

    if (n % 2 != 0)
    {
        n++;
    }

    char paddedX[MAX], paddedY[MAX];
    padLeft(paddedX, x, n);
    padLeft(paddedY, y, n);

    int mid = n / 2;

    char a[MAX], b[MAX], c[MAX], d[MAX];

    strncpy(a, paddedX, mid);
    a[mid] = '\0';
    strcpy(b, paddedX + mid);

    strncpy(c, paddedY, mid);
    c[mid] = '\0';
    strcpy(d, paddedY + mid);

    removeLeadingZeros(a);
    removeLeadingZeros(b);
    removeLeadingZeros(c);
    removeLeadingZeros(d);

    char ac[MAX], ad[MAX], bc[MAX], bd[MAX];
    multiply(a, c, ac);
    multiply(a, d, ad);
    multiply(b, c, bc);
    multiply(b, d, bd);

    char middleSum[MAX];
    addStrings(ad, bc, middleSum);

    char part1[MAX], part2[MAX];
    int i;

    strcpy(part1, ac);
    for (i = 0; i < n; i++)
    {
        strcat(part1, "0");
    }

    strcpy(part2, middleSum);
    for (i = 0; i < mid; i++)
    {
        strcat(part2, "0");
    }

    char combined[MAX];
    addStrings(part1, part2, combined);
    addStrings(combined, bd, result);
}

int main()
{
    char num1[MAX];
    char num2[MAX];
    char result[MAX * 2];

    if (scanf("%999s", num1) != 1 || scanf("%999s", num2) != 1)
    {
        printf("Error: Invalid large integer input\n");
        return 1;
    }

    int len1 = strlen(num1);
    int len2 = strlen(num2);

    if (len1 == 0 || len2 == 0)
    {
        printf("Error: Empty integer string\n");
        return 1;
    }

    if (len1 > 400 || len2 > 400)
    {
        printf("Error: Input integer string exceeds max length limit of 400 digits\n");
        return 1;
    }

    int i;
    for (i = 0; i < len1; i++)
    {
        if (num1[i] < '0' || num1[i] > '9')
        {
            printf("Error: First input contains non-digit character '%c'\n", num1[i]);
            return 1;
        }
    }

    for (i = 0; i < len2; i++)
    {
        if (num2[i] < '0' || num2[i] > '9')
        {
            printf("Error: Second input contains non-digit character '%c'\n", num2[i]);
            return 1;
        }
    }

    multiply(num1, num2, result);

    printf("First Large Integer  : %s\n", num1);
    printf("Second Large Integer : %s\n", num2);
    printf("Product = %s\n", result);

    return 0;
}
