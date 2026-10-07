// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eos/shell_cmd.h"
#include "eos/log.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef _WIN32
#include <sys/wait.h>
#endif

/* Reject anything a shell reads as syntax rather than as text.
 *
 * This rule was first written in services/linux/src/linux_security.c, where
 * the list it replaced -- ;|&><$()"' -- missed two that matter. A backtick
 * is command substitution in every POSIX shell, so /tmp/`id` passed as safe
 * and ran id. A newline ends one command and starts another, so a path
 * could append a whole second command. Both were reported SAFE. Control
 * characters and backslash are rejected for the same reason.
 *
 * A NULL value returns 0 -- "refuse" -- because that is the only right
 * default for a predicate guarding command construction. */
/* Windows (cmd.exe, then the program's own CRT argv parsing) reads a quoted
 * value differently from a POSIX shell:
 *   - A backslash is the path separator and means nothing inside double
 *     quotes, so refusing it refused every Windows path. eos clean, the
 *     cargo/pip/npm backends and the install tests all failed on the MSVC
 *     leg with "refusing a shell argument".
 *   - A backslash directly before the closing quote is different: the CRT
 *     reads \" as a literal quote, so "C:\dir\" swallows the arguments
 *     after it. A trailing backslash is refused.
 *   - %VAR% expands even inside double quotes, and so does !VAR! when
 *     delayed expansion is on. Both are refused. */
int eos_shell_arg_is_safe(const char *arg) {
    const unsigned char *p;
    if (!arg) return 0;
#ifdef _WIN32
    static const char refused[] = ";|&><$()\"'`%!";
#else
    static const char refused[] = ";|&><$()\"'`\\";
#endif
    for (p = (const unsigned char *)arg; *p; p++) {
        if (*p < 0x20 || *p == 0x7f) return 0;
        if (strchr(refused, (char)*p)) return 0;
    }
#ifdef _WIN32
    if (p != (const unsigned char *)arg && p[-1] == '\\') return 0;
#endif
    return 1;
}

/* Some programs read a token as one word whether or not it is quoted --
 * a make target, a CROSS_COMPILE prefix, a board name -- and there a single
 * space is already enough to turn one argument into two.
 *
 * The first version of this rule, also in linux_security.c, was a second
 * denylist -- space, tab, *, ?, ~ -- and it had the same shape of hole as
 * the first one: it missed [ and ] (a glob character class) and { } (brace
 * expansion, which /bin/sh performs when it is bash). Answering an
 * incomplete denylist with another denylist just moves the next gap further
 * out, so "one shell word" is written as the small positive definition it
 * has: isalnum() plus ._/+=:- covers every defconfig target, cross-compile
 * prefix, board name, hash algorithm name and hex digest this tree uses,
 * and an allowlist cannot be incomplete.
 *
 * A leading '-' is refused separately: it is built from allowed characters
 * but turns `make -C dir <target>` into an option rather than a target.
 *
 * The empty string is a word; callers that must not pass one check for
 * content before appending. */
int eos_shell_word_is_safe(const char *word) {
    const unsigned char *p;
    if (!word) return 0;
    if (word[0] == '-') return 0;
    for (p = (const unsigned char *)word; *p; p++) {
        if (isalnum(*p)) continue;
        if (strchr("._/+=:-", (char)*p)) continue;
        return 0;
    }
    return 1;
}

void eos_shell_cmd_init(EosShellCmd *cmd) {
    if (!cmd) return;
    cmd->buf[0] = '\0';
    cmd->len = 0;
    cmd->fault = 0;
}

/* Append raw bytes; on a miss mark the command faulty and leave it as it was,
 * so a truncated line can never be the one that runs. */
static void append_raw(EosShellCmd *cmd, const char *s) {
    size_t n;
    if (!cmd || cmd->fault) return;
    n = strlen(s);
    if (n >= sizeof(cmd->buf) - cmd->len) {
        cmd->fault = 1;
        return;
    }
    memcpy(cmd->buf + cmd->len, s, n + 1);
    cmd->len += n;
}

void eos_shell_cmd_text(EosShellCmd *cmd, const char *text) {
    if (!cmd || !text) { if (cmd) cmd->fault = 1; return; }
    append_raw(cmd, text);
}

void eos_shell_cmd_int(EosShellCmd *cmd, int value) {
    char digits[16];
    if (!cmd) return;
    snprintf(digits, sizeof(digits), "%d", value);
    append_raw(cmd, digits);
}

void eos_shell_cmd_arg(EosShellCmd *cmd, const char *arg) {
    if (!cmd) return;
    if (!eos_shell_arg_is_safe(arg)) {
        EOS_ERROR("refusing a shell argument that is not one quoted value: %s",
                  arg ? arg : "(null)");
        cmd->fault = 1;
        return;
    }
    /* The quotes and the value land together or not at all, so a value that
     * does not fit leaves no dangling quote behind. */
    if (strlen(arg) + 2 >= sizeof(cmd->buf) - cmd->len) {
        cmd->fault = 1;
        return;
    }
    append_raw(cmd, "\"");
    append_raw(cmd, arg);
    append_raw(cmd, "\"");
}

void eos_shell_cmd_word(EosShellCmd *cmd, const char *word) {
    if (!cmd) return;
    if (!eos_shell_word_is_safe(word)) {
        EOS_ERROR("refusing a shell argument that is not one word: %s",
                  word ? word : "(null)");
        cmd->fault = 1;
        return;
    }
    append_raw(cmd, word);
}

EosResult eos_shell_cmd_run(EosShellCmd *cmd, const char *what) {
    int rc;
    if (!cmd) return EOS_ERR_INVALID;
    if (cmd->fault) {
        EOS_ERROR("%s: command refused; an argument was unsafe or the line did not fit",
                  what ? what : "shell command");
        return EOS_ERR_INVALID;
    }
    EOS_INFO("%s: %s", what ? what : "shell command", cmd->buf);
    rc = system(cmd->buf);
    /* "The build failed" and "nothing ran at all" are different problems
     * for whoever reads the log: -1 is a shell that could not be started
     * (fork failed, or the status could not be collected), and a POSIX
     * shell exits 127 when it could not run the command it was given.
     * Both are the environment, not the build. */
    if (rc == -1) {
        EOS_ERROR("%s: could not run a shell at all", what ? what : "shell command");
        return EOS_ERR_SYSTEM;
    }
#ifndef _WIN32
    if (WIFEXITED(rc) && WEXITSTATUS(rc) == 127) {
        EOS_ERROR("%s: the shell could not run the command (exit 127)",
                  what ? what : "shell command");
        return EOS_ERR_SYSTEM;
    }
#endif
    return (rc == 0) ? EOS_OK : EOS_ERR_BUILD;
}
