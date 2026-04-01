// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "eni/config.h"
#include "eni/log.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

eni_status_t eni_config_init(eni_config_t *cfg)
{
    if (!cfg) return ENI_ERR_INVALID;
    memset(cfg, 0, sizeof(*cfg));
    cfg->variant = ENI_VARIANT_MIN;
    cfg->mode    = ENI_MODE_INTENT;
    cfg->filter.min_confidence = 0.80f;
    cfg->filter.debounce_ms    = 100;
    return ENI_OK;
}

eni_status_t eni_config_load_defaults(eni_config_t *cfg, eni_variant_t variant)
{
    if (!cfg) return ENI_ERR_INVALID;

    eni_config_init(cfg);
    cfg->variant = variant;

    if (variant == ENI_VARIANT_MIN) {
        cfg->mode = ENI_MODE_INTENT;
        cfg->providers[0].name      = "simulator";
        cfg->providers[0].transport = ENI_TRANSPORT_UNIX_SOCKET;
        cfg->provider_count         = 1;
        cfg->filter.min_confidence  = 0.80f;
        cfg->filter.debounce_ms     = 100;
    } else {
        cfg->mode = ENI_MODE_FEATURES_INTENT;
        cfg->providers[0].name      = "generic-decoder";
        cfg->providers[0].transport = ENI_TRANSPORT_GRPC;
        cfg->provider_count         = 1;
        cfg->routing.max_latency_ms = 20;
        cfg->routing.local_only     = true;
        cfg->observability.metrics  = true;
        cfg->observability.audit    = true;
        cfg->observability.trace    = false;
    }

    return ENI_OK;
}

static void trim_whitespace(char *s)
{
    char *start = s;
    while (*start == ' ' || *start == '\t') start++;
    if (start != s) memmove(s, start, strlen(start) + 1);
    if (*s == '\0') return;
    char *end = s + strlen(s) - 1;
    while (end > s && (*end == ' ' || *end == '\t' || *end == '\n' || *end == '\r'))
        end--;
    *(end + 1) = '\0';
}

static void config_apply_kv(eni_config_t *cfg, const char *key, const char *value)
{
    if (strcmp(key, "variant") == 0) {
        if (strcmp(value, "min") == 0)
            cfg->variant = ENI_VARIANT_MIN;
        else if (strcmp(value, "framework") == 0)
            cfg->variant = ENI_VARIANT_FRAMEWORK;
    } else if (strcmp(key, "mode") == 0) {
        if (strcmp(value, "intent") == 0)
            cfg->mode = ENI_MODE_INTENT;
        else if (strcmp(value, "features") == 0)
            cfg->mode = ENI_MODE_FEATURES;
        else if (strcmp(value, "raw") == 0)
            cfg->mode = ENI_MODE_RAW;
        else if (strcmp(value, "features_intent") == 0)
            cfg->mode = ENI_MODE_FEATURES_INTENT;
    } else if (strcmp(key, "confidence_threshold") == 0) {
        cfg->filter.min_confidence = (float)atof(value);
    } else if (strcmp(key, "debounce_ms") == 0) {
        cfg->filter.debounce_ms = (uint32_t)atoi(value);
    } else if (strcmp(key, "max_providers") == 0) {
        /* Cap to valid range; ENI_CONFIG_MAX_PROVIDERS defined in config.h */
        int n = atoi(value);
        cfg->provider_count = (n > 0 && n <= ENI_CONFIG_MAX_PROVIDERS) ? n : 0;
    } else if (strcmp(key, "default_deny") == 0) {
        cfg->policy.require_confirmation = (strcmp(value, "true") == 0);
    }
}

eni_status_t eni_config_load_file(eni_config_t *cfg, const char *path)
{
    if (!cfg || !path) return ENI_ERR_INVALID;

    FILE *fp = fopen(path, "r");
    if (!fp) {
        ENI_LOG_WARN("config", "cannot open config file: %s", path);
        return ENI_ERR_IO;
    }

    eni_config_init(cfg);

    char line[256];
    while (fgets(line, sizeof(line), fp)) {
        /* Skip comments and blank lines */
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '#' || *p == ';' || *p == '\n' || *p == '\r' || *p == '\0')
            continue;

        /* Split on '=' */
        char *eq = strchr(p, '=');
        if (!eq) continue;

        *eq = '\0';
        char *key = p;
        char *value = eq + 1;

        trim_whitespace(key);
        trim_whitespace(value);

        if (*key == '\0') continue;

        config_apply_kv(cfg, key, value);
    }

    fclose(fp);
    ENI_LOG_INFO("config", "loaded config from %s", path);
    return ENI_OK;
}

void eni_config_dump(const eni_config_t *cfg)
{
    if (!cfg) return;

    const char *var_str = cfg->variant == ENI_VARIANT_MIN ? "min" : "framework";
    const char *mode_str;
    switch (cfg->mode) {
    case ENI_MODE_INTENT:          mode_str = "intent";          break;
    case ENI_MODE_FEATURES:        mode_str = "features";        break;
    case ENI_MODE_RAW:             mode_str = "raw";             break;
    case ENI_MODE_FEATURES_INTENT: mode_str = "features+intent"; break;
    default:                       mode_str = "unknown";         break;
    }

    printf("[config] variant=%s mode=%s providers=%d\n",
           var_str, mode_str, cfg->provider_count);

    for (int i = 0; i < cfg->provider_count; i++) {
        printf("  provider[%d]: %s\n", i,
               cfg->providers[i].name ? cfg->providers[i].name : "(null)");
    }

    printf("  filter: confidence=%.2f debounce=%u ms\n",
           cfg->filter.min_confidence, cfg->filter.debounce_ms);
    printf("  observability: metrics=%d audit=%d trace=%d\n",
           cfg->observability.metrics, cfg->observability.audit,
           cfg->observability.trace);
}
