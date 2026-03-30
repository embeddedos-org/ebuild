// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include "mathlib.h"

int main(void) {
    int a = 12, b = 5;

    printf("Math Library Demo\n");
    printf("=================\n");
    printf("add(%d, %d)      = %d\n", a, b, math_add(a, b));
    printf("subtract(%d, %d) = %d\n", a, b, math_subtract(a, b));
    printf("multiply(%d, %d) = %d\n", a, b, math_multiply(a, b));
    printf("factorial(%d)    = %d\n", b, math_factorial(b));

    return 0;
}
