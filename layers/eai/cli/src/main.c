// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eai/common.h"
#include "eai/tools_builtin.h"
#include "eai/platform.h"
#include "eai_min/eai_min.h"
#include "eai_fw/eai_framework.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef EAI_EIPC_ENABLED
#include "eai/eipc_listener.h"
#endif

static void print_banner(void)
{
    printf("\n");
    printf("  ╔═══════════════════════════════════════╗\n");
    printf("  ║   EAI — AI Layer for Embedded Systems ║\n");
    printf("  ║   v%s                             ║\n", EAI_VERSION_STRING);
    printf("  ╚═══════════════════════════════════════╝\n");
    printf("\n");
}

static void print_usage(const char *prog)
{
    printf("Usage: %s <command> [options]\n\n", prog);
    printf("Commands:\n");
    printf("  run              Run AI agent with default config\n");
    printf("  serve            Start AI inference server\n");
    printf("  status           Show system status\n");
    printf("  tools            List available tools\n");
    printf("  profile <name>   Load a deployment profile\n");
    printf("  config <file>    Load configuration from file\n");
    printf("  version          Show version information\n");
    printf("  help             Show this help message\n");
    printf("\n");
    printf("Profiles:\n");
    printf("  smart-camera       Vision-focused edge deployment\n");
    printf("  industrial-gateway Full industrial IoT gateway\n");
    printf("  robot-controller   Real-time robotics control\n");
    printf("  mobile-edge        Lightweight mobile deployment\n");
    printf("\n");
    printf("Examples:\n");
    printf("  %s run\n", prog);
    printf("  %s serve --model phi-mini\n", prog);
    printf("  %s profile industrial-gateway\n", prog);
    printf("\n");
}

static int cmd_version(void)
{
    print_banner();
    printf("  Version:   %s\n", EAI_VERSION_STRING);
    printf("  Variants:  EAI-Min, EAI-Framework\n");
    printf("  Built-in:  mqtt.publish, device.read_sensor, http.get\n");
    printf("  Protocols: MQTT, OPC-UA, Modbus, CAN\n");
    printf("\n");
    return 0;
}

static int cmd_status(void)
{
    print_banner();

    /* Platform info */
    eai_platform_t plat;
    eai_platform_detect(&plat);

    char device_info[256] = {0};
    if (plat.initialized && plat.ops->get_device_info) {
        plat.ops->get_device_info(&plat, device_info, sizeof(device_info));
    }

    uint64_t total_mem = 0, avail_mem = 0;
    if (plat.initialized && plat.ops->get_memory_info) {
        plat.ops->get_memory_info(&plat, &total_mem, &avail_mem);
    }

    printf("System Status:\n");
    printf("  platform:  %s\n", plat.initialized ? plat.ops->name : "unknown");
    printf("  device:    %s\n", device_info[0] ? device_info : "unknown");
    printf("  memory:    %llu MB total, %llu MB available\n",
           (unsigned long long)(total_mem / (1024 * 1024)),
           (unsigned long long)(avail_mem / (1024 * 1024)));
    printf("  EAI:       v%s\n", EAI_VERSION_STRING);
    printf("\n");

    eai_platform_shutdown(&plat);
    return 0;
}

static int cmd_tools(void)
{
    eai_tool_registry_t reg;
    eai_tool_registry_init(&reg);
    eai_tools_register_builtins(&reg);

    print_banner();
    eai_tool_registry_list(&reg);
    return 0;
}

static int cmd_profile(const char *profile_name)
{
    eai_config_t cfg;
    eai_config_init(&cfg);

    eai_status_t s = eai_config_load_profile(&cfg, profile_name);
    if (s != EAI_OK) {
        fprintf(stderr, "Error: unknown profile '%s'\n", profile_name);
        return 1;
    }

    print_banner();
    printf("Profile: %s\n\n", profile_name);
    eai_config_dump(&cfg);
    return 0;
}

static int cmd_run(const eai_config_t *cfg)
{
    print_banner();
    printf("Starting EAI agent...\n\n");

    /* Initialize tool registry */
    eai_tool_registry_t tools;
    eai_tool_registry_init(&tools);
    eai_tools_register_builtins(&tools);

    if (cfg->variant == EAI_VARIANT_MIN) {
        printf("Mode: EAI-Min (lightweight)\n\n");

        /* Create runtime */
        eai_min_runtime_t runtime;
        eai_min_runtime_create(&runtime, EAI_RUNTIME_LLAMA_CPP);

        /* Load stub model */
        eai_model_manifest_t manifest = {0};
        strncpy(manifest.name, "phi-mini-q4", sizeof(manifest.name) - 1);
        manifest.kind = EAI_MODEL_LLM;
        manifest.runtime = EAI_RUNTIME_LLAMA_CPP;
        strncpy(manifest.version, "1.0.0", sizeof(manifest.version) - 1);
        manifest.footprint.ram_mb = 2048;
        manifest.footprint.storage_mb = 2300;

        eai_min_runtime_load(&runtime, "models/phi-mini-q4.gguf", &manifest);

        /* Create memory */
        eai_mem_lite_t memory;
        eai_mem_lite_init(&memory, NULL);

        /* Create and run agent */
        eai_min_agent_t agent;
        eai_min_agent_init(&agent, &runtime, &tools, &memory);

        eai_agent_task_t task = {
            .goal = "Monitor sensors and report anomalies",
            .offline_only = true,
            .max_iterations = 3,
        };

        eai_status_t s = eai_min_agent_run(&agent, &task);
        printf("\nAgent result: %s\n", eai_status_str(s));
        printf("Output: %s\n", eai_min_agent_output(&agent));

        eai_min_runtime_destroy(&runtime);
    }
    else {
        printf("Mode: EAI-Framework (industrial)\n\n");

        /* Runtime manager */
        eai_fw_runtime_manager_t rt_mgr;
        eai_fw_rtmgr_init(&rt_mgr);

        extern const eai_runtime_ops_t eai_runtime_stub_ops;
        eai_fw_rtmgr_add(&rt_mgr, &eai_runtime_stub_ops);

        /* Connector manager */
        eai_fw_connector_mgr_t conn_mgr;
        eai_fw_conn_mgr_init(&conn_mgr);

        for (int i = 0; i < cfg->connector_count; i++) {
            if (strcmp(cfg->connectors[i], "mqtt") == 0)
                eai_fw_conn_add(&conn_mgr, "mqtt", &eai_connector_mqtt_ops);
            else if (strcmp(cfg->connectors[i], "opcua") == 0)
                eai_fw_conn_add(&conn_mgr, "opcua", &eai_connector_opcua_ops);
            else if (strcmp(cfg->connectors[i], "modbus") == 0)
                eai_fw_conn_add(&conn_mgr, "modbus", &eai_connector_modbus_ops);
            else if (strcmp(cfg->connectors[i], "can") == 0)
                eai_fw_conn_add(&conn_mgr, "can", &eai_connector_can_ops);
        }

        eai_fw_conn_connect_all(&conn_mgr, NULL, 0);

        /* Policy */
        eai_fw_policy_t policy;
        eai_fw_policy_init(&policy);

        /* Observability */
        eai_fw_observability_t obs;
        eai_fw_obs_init(&obs, cfg->observability);
        eai_fw_obs_counter_inc(&obs, "eai.startup", 1);

        /* Orchestrator */
        eai_fw_orchestrator_t orch;
        eai_fw_orch_init(&orch, &rt_mgr, &tools, &conn_mgr, &policy);

        printf("Framework initialized:\n");
        printf("  Runtimes:    %d\n", rt_mgr.count);
        printf("  Connectors:  %d\n", conn_mgr.count);
        printf("  Tools:       %d\n", tools.count);
        printf("  Observability: %s\n", cfg->observability ? "on" : "off");
        printf("\nReady for workflow execution.\n");

        /* Cleanup */
        eai_fw_conn_disconnect_all(&conn_mgr);
        eai_fw_rtmgr_shutdown(&rt_mgr);
    }

    return 0;
}

int main(int argc, char *argv[])
{
    eai_log_set_level(EAI_LOG_INFO);

    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    const char *cmd = argv[1];

    if (strcmp(cmd, "version") == 0 || strcmp(cmd, "--version") == 0 || strcmp(cmd, "-v") == 0) {
        return cmd_version();
    }
    if (strcmp(cmd, "help") == 0 || strcmp(cmd, "--help") == 0 || strcmp(cmd, "-h") == 0) {
        print_usage(argv[0]);
        return 0;
    }
    if (strcmp(cmd, "status") == 0) {
        return cmd_status();
    }
    if (strcmp(cmd, "tools") == 0) {
        return cmd_tools();
    }
    if (strcmp(cmd, "profile") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Error: profile name required\n");
            return 1;
        }
        return cmd_profile(argv[2]);
    }
    if (strcmp(cmd, "run") == 0) {
        eai_config_t cfg;
        eai_config_init(&cfg);

        /* Check for --profile flag */
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--profile") == 0 && i + 1 < argc) {
                eai_config_load_profile(&cfg, argv[i + 1]);
                i++;
            }
            else if (strcmp(argv[i], "--config") == 0 && i + 1 < argc) {
                eai_config_load_file(&cfg, argv[i + 1]);
                i++;
            }
        }

        return cmd_run(&cfg);
    }
    if (strcmp(cmd, "serve") == 0) {
#ifdef EAI_EIPC_ENABLED
        const char *port = "9090";
        const char *hmac_key = NULL;
        for (int i = 2; i < argc; i++) {
            if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) port = argv[++i];
            if (strcmp(argv[i], "--hmac-key") == 0 && i + 1 < argc) hmac_key = argv[++i];
        }
        if (!hmac_key) {
            fprintf(stderr, "Usage: eai serve --port PORT --hmac-key KEY\n");
            return 1;
        }

        char addr[64];
        snprintf(addr, sizeof(addr), "127.0.0.1:%s", port);

        eai_min_runtime_t runtime;
        eai_min_runtime_create(&runtime, EAI_RUNTIME_LLAMA_CPP);
        eai_tool_registry_t tools;
        eai_tool_registry_init(&tools);
        eai_tools_register_builtins(&tools);
        eai_mem_lite_t memory;
        eai_mem_lite_init(&memory, NULL);
        eai_min_agent_t agent;
        eai_min_agent_init(&agent, &runtime, &tools, &memory);

        eai_eipc_listener_t listener;
        eai_eipc_listener_init(&listener);
        eai_eipc_listener_start(&listener, addr, hmac_key);
        printf("EAI server listening on %s...\n", addr);

        eai_eipc_listener_accept(&listener);
        printf("Client connected.\n");

        while (1) {
            char intent[64];
            float confidence;
            eai_status_t st = eai_eipc_listener_receive_intent(
                &listener, intent, sizeof(intent), &confidence);
            if (st != EAI_OK) break;

            printf("Received intent: %s (%.2f)\n", intent, confidence);

            char goal[256];
            snprintf(goal, sizeof(goal),
                     "Execute neural intent: %s (confidence: %.2f)",
                     intent, confidence);
            eai_agent_task_t task = {
                .goal = goal, .offline_only = true, .max_iterations = 3
            };
            eai_min_agent_run(&agent, &task);

            eai_eipc_listener_send_ack(&listener, "", "ok");
            eai_min_agent_reset(&agent);
        }

        eai_eipc_listener_close(&listener);
        return 0;
#else
        printf("EIPC not enabled. Rebuild with -DEAI_EIPC_ENABLED=ON\n");
        return 1;
#endif
    }
    if (strcmp(cmd, "config") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Error: config file path required\n");
            return 1;
        }
        eai_config_t cfg;
        eai_config_init(&cfg);
        eai_status_t s = eai_config_load_file(&cfg, argv[2]);
        if (s != EAI_OK) {
            fprintf(stderr, "Error loading config: %s\n", eai_status_str(s));
            return 1;
        }
        print_banner();
        eai_config_dump(&cfg);
        return 0;
    }

    fprintf(stderr, "Unknown command: %s\n", cmd);
    print_usage(argv[0]);
    return 1;
}
