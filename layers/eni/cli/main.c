// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "eni/common.h"
#include "eni_min/service.h"
#include "eni_fw/service.h"
#include "eni_platform/platform.h"
#include "simulator.h"

static eni_status_t tool_cursor_move(const eni_tool_call_t *call, eni_tool_result_t *result)
{
    (void)call;
    const char *msg = "cursor moved";
    size_t len = strlen(msg);
    memcpy(result->data, msg, len);
    result->len = len;
    result->status = ENI_OK;
    return ENI_OK;
}

static eni_status_t tool_select(const eni_tool_call_t *call, eni_tool_result_t *result)
{
    (void)call;
    const char *msg = "selection made";
    size_t len = strlen(msg);
    memcpy(result->data, msg, len);
    result->len = len;
    result->status = ENI_OK;
    return ENI_OK;
}

static void print_usage(void)
{
    printf("ENI — Neural Interface Adapter v%s\n\n", ENI_VERSION_STRING);
    printf("Usage: eni <command> [options]\n\n");
    printf("Commands:\n");
    printf("  run-min       Run ENI-Min with simulator provider\n");
    printf("  run-fw        Run ENI-Framework with simulator provider\n");
    printf("  info          Show platform information\n");
    printf("  version       Show version\n");
    printf("  help          Show this help\n");
}

static int cmd_info(void)
{
    eni_platform_init();
    eni_platform_info_t pi = eni_platform_info();

    printf("ENI v%s\n", ENI_VERSION_STRING);
    printf("Platform: %s (%s)\n", pi.os_name, pi.arch);
    printf("Real-time: %s\n", pi.realtime_capable ? "yes" : "no");
    printf("Hardware:  %s\n", pi.hardware_access  ? "yes" : "no");
    return 0;
}

static int cmd_run_min(int ticks)
{
    eni_config_t cfg;
    eni_config_load_defaults(&cfg, ENI_VARIANT_MIN);

    eni_min_service_t svc;
    eni_status_t st = eni_min_service_init(&svc, &cfg, &eni_provider_simulator_ops);
    if (st != ENI_OK) {
        fprintf(stderr, "init failed: %s\n", eni_status_str(st));
        return 1;
    }

    /* Register mappings */
    eni_min_mapper_add(&svc.mapper, "move_left",    "ui.cursor.move");
    eni_min_mapper_add(&svc.mapper, "move_right",   "ui.cursor.move");
    eni_min_mapper_add(&svc.mapper, "select",       "ui.select");
    eni_min_mapper_add(&svc.mapper, "scroll_up",    "ui.cursor.move");
    eni_min_mapper_add(&svc.mapper, "scroll_down",  "ui.cursor.move");
    eni_min_mapper_add(&svc.mapper, "activate",     "ui.select");
    eni_min_mapper_add(&svc.mapper, "deactivate",   "ui.select");

    /* Register tools */
    eni_tool_entry_t cursor_tool = { .name = "ui.cursor.move", .description = "Move cursor", .exec = tool_cursor_move };
    eni_tool_entry_t select_tool = { .name = "ui.select", .description = "Select item", .exec = tool_select };
    eni_min_tool_bridge_register(&svc.tool_bridge, &cursor_tool);
    eni_min_tool_bridge_register(&svc.tool_bridge, &select_tool);

    st = eni_min_service_start(&svc);
    if (st != ENI_OK) {
        fprintf(stderr, "start failed: %s\n", eni_status_str(st));
        return 1;
    }

    printf("ENI-Min running (simulator, %d ticks)...\n", ticks);
    for (int i = 0; i < ticks; i++) {
        eni_min_service_tick(&svc);
    }

    eni_min_service_stats(&svc);
    eni_min_service_shutdown(&svc);
    return 0;
}

static int cmd_run_fw(int ticks)
{
    eni_config_t cfg;
    eni_config_load_defaults(&cfg, ENI_VARIANT_FRAMEWORK);

    eni_fw_service_t svc;
    eni_status_t st = eni_fw_service_init(&svc, &cfg);
    if (st != ENI_OK) {
        fprintf(stderr, "init failed: %s\n", eni_status_str(st));
        return 1;
    }

    st = eni_fw_service_add_provider(&svc, &eni_provider_simulator_ops, "simulator");
    if (st != ENI_OK) {
        fprintf(stderr, "add provider failed: %s\n", eni_status_str(st));
        return 1;
    }

    st = eni_fw_service_start(&svc);
    if (st != ENI_OK) {
        fprintf(stderr, "start failed: %s\n", eni_status_str(st));
        return 1;
    }

    printf("ENI-Framework running (simulator, %d ticks)...\n", ticks);
    for (int i = 0; i < ticks; i++) {
        eni_fw_service_tick(&svc);
    }

    eni_fw_service_stats(&svc);
    eni_fw_service_shutdown(&svc);
    return 0;
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        print_usage();
        return 0;
    }

    eni_log_set_level(ENI_LOG_INFO);

    const char *cmd = argv[1];

    if (strcmp(cmd, "version") == 0) {
        printf("ENI v%s\n", ENI_VERSION_STRING);
        return 0;
    }

    if (strcmp(cmd, "help") == 0) {
        print_usage();
        return 0;
    }

    if (strcmp(cmd, "info") == 0) {
        return cmd_info();
    }

    int ticks = 30;
    if (argc >= 3) {
        ticks = atoi(argv[2]);
        if (ticks <= 0) ticks = 30;
    }

    if (strcmp(cmd, "run-min") == 0) {
        return cmd_run_min(ticks);
    }

    if (strcmp(cmd, "run-fw") == 0) {
        return cmd_run_fw(ticks);
    }

    fprintf(stderr, "Unknown command: %s\n", cmd);
    print_usage();
    return 1;
}
