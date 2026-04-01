// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_NEURALINK_H
#define ENI_NEURALINK_H

#include "eni/provider_contract.h"
#include "eni/types.h"

#ifdef __cplusplus
extern "C" {
#endif

#define ENI_NEURALINK_MAX_CHANNELS   1024
#define ENI_NEURALINK_SAMPLE_RATE    30000
#define ENI_NEURALINK_PACKET_SIZE    256

typedef enum {
    ENI_NL_MODE_RAW       = 0,
    ENI_NL_MODE_DECODED   = 1,
    ENI_NL_MODE_INTENT    = 2,
    ENI_NL_MODE_MOTOR     = 3
} eni_nl_mode_t;

typedef enum {
    ENI_NL_STATE_DISCONNECTED = 0,
    ENI_NL_STATE_CONNECTING   = 1,
    ENI_NL_STATE_STREAMING    = 2,
    ENI_NL_STATE_CALIBRATING  = 3,
    ENI_NL_STATE_ERROR        = 4
} eni_nl_state_t;

typedef struct {
    float    channel_data[ENI_NEURALINK_PACKET_SIZE];
    uint32_t channel_count;
    uint32_t sample_index;
    uint64_t timestamp_us;
    uint8_t  electrode_id;
    float    signal_quality;
} eni_nl_packet_t;

typedef struct {
    char     device_id[64];
    char     firmware_version[32];
    uint32_t electrode_count;
    uint32_t sample_rate;
    float    battery_pct;
    float    temperature_c;
    eni_nl_state_t state;
    uint64_t packets_received;
    uint64_t packets_dropped;
    float    avg_latency_ms;
} eni_nl_status_t;

typedef struct {
    eni_nl_mode_t  mode;
    uint32_t       channels;
    uint32_t       sample_rate;
    char           device_addr[64];
    float          signal_threshold;
    int            auto_calibrate;
    int            filter_enabled;
    float          bandpass_low_hz;
    float          bandpass_high_hz;
    float          notch_freq_hz;
    void         (*on_packet)(const eni_nl_packet_t *pkt, void *ctx);
    void         (*on_intent)(const char *intent, float confidence, void *ctx);
    void          *user_ctx;
} eni_nl_config_t;

/* Lifecycle */
int  eni_neuralink_init(const eni_nl_config_t *cfg);
void eni_neuralink_deinit(void);
int  eni_neuralink_connect(const char *device_addr);
int  eni_neuralink_disconnect(void);

/* Data acquisition */
int  eni_neuralink_start_stream(void);
int  eni_neuralink_stop_stream(void);
int  eni_neuralink_read_packet(eni_nl_packet_t *pkt);

/* Calibration */
int  eni_neuralink_calibrate(uint32_t duration_ms);
int  eni_neuralink_set_threshold(float threshold);

/* Intent decoding */
int  eni_neuralink_decode_intent(const eni_nl_packet_t *pkt,
                                  char *intent, int maxlen, float *confidence);

/* Status */
int  eni_neuralink_get_status(eni_nl_status_t *status);
eni_nl_state_t eni_neuralink_get_state(void);

/* Provider registration — integrates with ENI provider framework */
const eni_provider_ops_t *eni_neuralink_get_provider(void);

#ifdef __cplusplus
}
#endif

#endif /* ENI_NEURALINK_H */