// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file shell_cmd.h
 * @brief A shell command built from configuration, checked before it runs.
 *
 * The build backends and the Linux security service hand commands to
 * system(). The text of those commands is written in this tree, but the
 * paths, targets and option values in them come from a project's
 * configuration. Two things went wrong with that before this file existed:
 * a value carrying shell metacharacters ran as shell, and a command that did
 * not fit its buffer ran truncated. Both are refused here, in one place.
 *
 * Usage:
 *
 *     EosShellCmd cmd;
 *     eos_shell_cmd_init(&cmd);
 *     eos_shell_cmd_text(&cmd, "cmake -S ");
 *     eos_shell_cmd_arg(&cmd, src_dir);        // double-quoted, checked
 *     eos_shell_cmd_text(&cmd, " -B ");
 *     eos_shell_cmd_arg(&cmd, build_dir);
 *     return eos_shell_cmd_run(&cmd, "CMake configure");
 *
 * eos_shell_cmd_text() is for program text written in this tree only.
 * Everything that originates in configuration goes through
 * eos_shell_cmd_arg() (quoted) or eos_shell_cmd_word() (unquoted, where the
 * program treats the token as one word). A refused value or an overflow
 * marks the command faulty; every later append is a no-op and
 * eos_shell_cmd_run() returns EOS_ERR_INVALID without running anything.
 */

#ifndef EOS_SHELL_CMD_H
#define EOS_SHELL_CMD_H

#include <stddef.h>
#include "eos/error.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Longest command the builder holds, terminator included. */
#define EOS_SHELL_CMD_MAX 4096

typedef struct {
    char   buf[EOS_SHELL_CMD_MAX];
    size_t len;
    int    fault;   /**< non-zero once something was refused or did not fit */
} EosShellCmd;

/** @brief Start an empty command. */
void eos_shell_cmd_init(EosShellCmd *cmd);

/**
 * @brief Append program text written in this tree.
 *
 * Not for configuration values: nothing is checked or quoted.
 */
void eos_shell_cmd_text(EosShellCmd *cmd, const char *text);

/** @brief Append a decimal integer (a job count, a port). */
void eos_shell_cmd_int(EosShellCmd *cmd, int value);

/**
 * @brief Append a configuration value as one double-quoted argument.
 *
 * Refused unless eos_shell_arg_is_safe() accepts it.
 */
void eos_shell_cmd_arg(EosShellCmd *cmd, const char *arg);

/**
 * @brief Append a configuration value unquoted, as one shell word.
 *
 * For tokens the program reads as a single word (a make target, a board
 * name, a cross-compile prefix). Refused unless eos_shell_word_is_safe()
 * accepts it.
 */
void eos_shell_cmd_word(EosShellCmd *cmd, const char *word);

/**
 * @brief Whether a configuration value may appear inside a double-quoted
 * shell argument.
 *
 * Refuses NULL, control characters and DEL, and every character that a
 * POSIX shell reads inside or around double quotes: ; | & > < $ ( ) " ' ` \.
 * This is the rule services/linux/src/linux_security.c reviewed and shipped
 * as is_path_safe(), unchanged. The empty string is accepted; an empty
 * argument is "" and the program it reaches decides what that means.
 *
 * cmd.exe, which the Windows install commands reach, also expands %NAME%
 * inside quotes. That substitutes text; it does not run any. A percent
 * sign is therefore not refused, so a Windows path with one still works.
 */
int eos_shell_arg_is_safe(const char *arg);

/**
 * @brief Whether a configuration value is one shell word.
 *
 * Positive definition: isalnum() and . _ / + = : - and nothing else, so an
 * incomplete denylist cannot be the next gap. A leading '-' is refused
 * separately: it is built from allowed characters but turns a target into
 * an option. The empty string is a word.
 */
int eos_shell_word_is_safe(const char *word);

/**
 * @brief Run the command through system().
 *
 * @param cmd   The command. A faulty one is refused with EOS_ERR_INVALID
 *              and logged, and nothing runs.
 * @param what  Short description for the log ("CMake configure").
 * @return EOS_OK when the command exited 0, EOS_ERR_BUILD when it did not,
 *         EOS_ERR_SYSTEM when no shell could be started or the shell could
 *         not run the command at all (exit 127), EOS_ERR_INVALID when the
 *         command was refused before anything ran.
 */
EosResult eos_shell_cmd_run(EosShellCmd *cmd, const char *what);

#ifdef __cplusplus
}
#endif

#endif /* EOS_SHELL_CMD_H */
