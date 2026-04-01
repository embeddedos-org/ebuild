// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eosuite.h"
#include "platform.h"
#include <math.h>
#include <ctype.h>

static double last_result = 0.0;
static int has_last_result = 0;

typedef struct {
    double values[256];
    int top;
} ValueStack;

typedef struct {
    char ops[256];
    int top;
} OpStack;

static void val_push(ValueStack *s, double v) {
    if (s->top < 255) s->values[++(s->top)] = v;
}

static double val_pop(ValueStack *s) {
    if (s->top >= 0) return s->values[(s->top)--];
    return 0.0;
}

static void op_push(OpStack *s, char c) {
    if (s->top < 255) s->ops[++(s->top)] = c;
}

static char op_pop(OpStack *s) {
    if (s->top >= 0) return s->ops[(s->top)--];
    return '\0';
}

static char op_peek(OpStack *s) {
    if (s->top >= 0) return s->ops[s->top];
    return '\0';
}

static int precedence(char op) {
    switch (op) {
        case '+': case '-': return 1;
        case '*': case '/': case '%': return 2;
        case '^': return 3;
        default: return 0;
    }
}

static int is_right_assoc(char op) {
    return op == '^';
}

static double apply_op(char op, double a, double b) {
    switch (op) {
        case '+': return a + b;
        case '-': return a - b;
        case '*': return a * b;
        case '/': return (b != 0.0) ? a / b : 0.0;
        case '%': return (b != 0.0) ? fmod(a, b) : 0.0;
        case '^': return pow(a, b);
        default: return 0.0;
    }
}

static void process_op(ValueStack *vals, OpStack *ops) {
    char op = op_pop(ops);
    double b = val_pop(vals);
    double a = val_pop(vals);
    val_push(vals, apply_op(op, a, b));
}

static int evaluate(const char *expr, double *result) {
    ValueStack vals;
    OpStack ops;
    vals.top = -1;
    ops.top = -1;

    const char *p = expr;
    int expect_operand = 1;

    while (*p) {
        if (isspace((unsigned char)*p)) {
            p++;
            continue;
        }

        if (*p == '(' ) {
            op_push(&ops, '(');
            p++;
            expect_operand = 1;
            continue;
        }

        if (*p == ')') {
            while (ops.top >= 0 && op_peek(&ops) != '(')
                process_op(&vals, &ops);
            if (ops.top >= 0) op_pop(&ops);
            p++;
            expect_operand = 0;
            continue;
        }

        if (expect_operand && (*p == '-' || *p == '+') &&
            (p == expr || *(p-1) == '(' || strchr("+-*/%^", *(p-1)))) {
            int neg = (*p == '-') ? 1 : 0;
            p++;
            while (isspace((unsigned char)*p)) p++;

            if (strncmp(p, "ans", 3) == 0 && !isalnum((unsigned char)p[3])) {
                double v = has_last_result ? last_result : 0.0;
                val_push(&vals, neg ? -v : v);
                p += 3;
            } else if (isdigit((unsigned char)*p) || *p == '.') {
                char *end;
                double v = strtod(p, &end);
                val_push(&vals, neg ? -v : v);
                p = end;
            } else {
                return 0;
            }
            expect_operand = 0;
            continue;
        }

        if (expect_operand && strncmp(p, "ans", 3) == 0 && !isalnum((unsigned char)p[3])) {
            val_push(&vals, has_last_result ? last_result : 0.0);
            p += 3;
            expect_operand = 0;
            continue;
        }

        if (expect_operand && (isdigit((unsigned char)*p) || *p == '.')) {
            char *end;
            double v = strtod(p, &end);
            val_push(&vals, v);
            p = end;
            expect_operand = 0;
            continue;
        }

        if (!expect_operand && strchr("+-*/%^", *p)) {
            char op = *p;
            while (ops.top >= 0 && op_peek(&ops) != '(' &&
                   (precedence(op_peek(&ops)) > precedence(op) ||
                    (precedence(op_peek(&ops)) == precedence(op) && !is_right_assoc(op)))) {
                process_op(&vals, &ops);
            }
            op_push(&ops, op);
            p++;
            expect_operand = 1;
            continue;
        }

        return 0;
    }

    while (ops.top >= 0) {
        if (op_peek(&ops) == '(') return 0;
        process_op(&vals, &ops);
    }

    if (vals.top != 0) return 0;
    *result = vals.values[0];
    return 1;
}

void run_calculator(void) {
    char input[MAX_INPUT_LEN];

    CLEAR_SCREEN();
    term_set_color(COLOR_CYAN, COLOR_BLACK);
    printf("\n  +==============================+\n");
    printf("  |        CALCULATOR            |\n");
    printf("  +==============================+\n");
    term_reset_color();
    printf("  Operators: + - * / ^ %% ()\n");
    printf("  Use 'ans' to recall last result\n");
    printf("  Type 'quit' to exit\n\n");

    for (;;) {
        term_set_color(COLOR_GREEN, COLOR_BLACK);
        printf("calc> ");
        term_reset_color();
        fflush(stdout);

        if (!fgets(input, sizeof(input), stdin)) break;
        input[strcspn(input, "\r\n")] = '\0';

        if (strlen(input) == 0) continue;
        if (strcmp(input, "quit") == 0 || strcmp(input, "exit") == 0) break;

        double result;
        if (evaluate(input, &result)) {
            last_result = result;
            has_last_result = 1;
            term_set_color(COLOR_YELLOW, COLOR_BLACK);
            if (result == (long long)result && fabs(result) < 1e15)
                printf("  = %lld\n", (long long)result);
            else
                printf("  = %.10g\n", result);
            term_reset_color();
        } else {
            term_set_color(COLOR_RED, COLOR_BLACK);
            printf("  Error: invalid expression\n");
            term_reset_color();
        }
    }
}
