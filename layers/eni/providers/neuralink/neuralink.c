// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#include "neuralink.h"
#include "eni/log.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

static struct {
    eni_nl_config_t cfg;
    eni_nl_state_t  state;
    eni_nl_status_t status;
    int             initialized;
    uint64_t        packet_idx;
    float           calibration_baseline[ENI_NEURALINK_PACKET_SIZE];
    int             calibrated;
} g_nl;

int eni_neuralink_init(const eni_nl_config_t *cfg) {
    if (!cfg) return -1;
    memset(&g_nl, 0, sizeof(g_nl));
    g_nl.cfg = *cfg;
    g_nl.state = ENI_NL_STATE_DISCONNECTED;
    if (g_nl.cfg.channels == 0) g_nl.cfg.channels = 32;
    if (g_nl.cfg.sample_rate == 0) g_nl.cfg.sample_rate = ENI_NEURALINK_SAMPLE_RATE;
    if (g_nl.cfg.signal_threshold <= 0) g_nl.cfg.signal_threshold = 0.5f;
    if (g_nl.cfg.bandpass_low_hz <= 0) g_nl.cfg.bandpass_low_hz = 0.5f;
    if (g_nl.cfg.bandpass_high_hz <= 0) g_nl.cfg.bandpass_high_hz = 300.0f;
    if (g_nl.cfg.notch_freq_hz <= 0) g_nl.cfg.notch_freq_hz = 60.0f;
    g_nl.initialized = 1;
    strncpy(g_nl.status.firmware_version, "0.1.0", 31);
    g_nl.status.electrode_count = g_nl.cfg.channels;
    g_nl.status.sample_rate = g_nl.cfg.sample_rate;
    g_nl.status.battery_pct = 100.0f;
    return 0;
}

void eni_neuralink_deinit(void) {
    if (g_nl.state == ENI_NL_STATE_STREAMING) eni_neuralink_stop_stream();
    if (g_nl.state != ENI_NL_STATE_DISCONNECTED) eni_neuralink_disconnect();
    g_nl.initialized = 0;
}

int eni_neuralink_connect(const char *device_addr) {
    if (!g_nl.initialized) return -1;
    if (g_nl.state != ENI_NL_STATE_DISCONNECTED) return -1;
    g_nl.state = ENI_NL_STATE_CONNECTING;
    if (device_addr) strncpy(g_nl.status.device_id, device_addr, 63);
    else strncpy(g_nl.status.device_id, "neuralink-sim-0", 63);
    g_nl.state = ENI_NL_STATE_STREAMING;
    g_nl.status.state = ENI_NL_STATE_STREAMING;
    return 0;
}

int eni_neuralink_disconnect(void) {
    if (!g_nl.initialized) return -1;
    if (g_nl.state == ENI_NL_STATE_STREAMING) eni_neuralink_stop_stream();
    g_nl.state = ENI_NL_STATE_DISCONNECTED;
    g_nl.status.state = ENI_NL_STATE_DISCONNECTED;
    return 0;
}

int eni_neuralink_start_stream(void) {
    if (!g_nl.initialized || g_nl.state != ENI_NL_STATE_STREAMING) return -1;
    return 0;
}

int eni_neuralink_stop_stream(void) {
    if (!g_nl.initialized) return -1;
    return 0;
}

static float bandpass_filter(float sample, float low, float high, float fs) {
    /* Simple 1st-order IIR approximation */
    float dt = 1.0f / fs;
    float rc_low = 1.0f / (2.0f * 3.14159f * low);
    float rc_high = 1.0f / (2.0f * 3.14159f * high);
    float alpha_high = dt / (rc_high + dt);
    float alpha_low = rc_low / (rc_low + dt);
    return sample * alpha_high * alpha_low;
}

int eni_neuralink_read_packet(eni_nl_packet_t *pkt) {
    if (!g_nl.initialized || !pkt || g_nl.state != ENI_NL_STATE_STREAMING) return -1;
    memset(pkt, 0, sizeof(*pkt));
    pkt->channel_count = g_nl.cfg.channels;
    if (pkt->channel_count > ENI_NEURALINK_PACKET_SIZE)
        pkt->channel_count = ENI_NEURALINK_PACKET_SIZE;
    pkt->sample_index = (uint32_t)(g_nl.packet_idx & 0xFFFFFFFF);
    pkt->timestamp_us = g_nl.packet_idx * (1000000ULL / g_nl.cfg.sample_rate);
    pkt->signal_quality = 0.95f;

    /* Generate simulated neural data (realistic spike patterns) */
    for (uint32_t ch = 0; ch < pkt->channel_count; ch++) {
        float t = (float)g_nl.packet_idx / (float)g_nl.cfg.sample_rate;
        /* Background neural noise (~10uV) */
        float noise = ((float)(g_nl.packet_idx * 7 + ch * 13) / 1000.0f);
        noise = noise - (float)(int)noise; /* fract */
        noise = (noise - 0.5f) * 20.0f; /* ±10uV */
        /* Alpha rhythm (8-12 Hz) */
        float alpha = 15.0f * sinf(2.0f * 3.14159f * 10.0f * t + (float)ch * 0.1f);
        /* Occasional spike (simulated action potential) */
        float spike = 0.0f;
        if (((g_nl.packet_idx + ch * 37) % 500) < 3)
            spike = 80.0f * expf(-fabsf(t * 1000.0f - (float)(g_nl.packet_idx % 500)) * 2.0f);
        float raw = noise + alpha + spike;
        /* Apply bandpass filter if enabled */
        if (g_nl.cfg.filter_enabled)
            raw = bandpass_filter(raw, g_nl.cfg.bandpass_low_hz, g_nl.cfg.bandpass_high_hz,
                                 (float)g_nl.cfg.sample_rate);
        /* Subtract baseline if calibrated */
        if (g_nl.calibrated)
            raw -= g_nl.calibration_baseline[ch];
        pkt->channel_data[ch] = raw;
    }

    g_nl.packet_idx++;
    g_nl.status.packets_received++;
    if (g_nl.cfg.on_packet)
        g_nl.cfg.on_packet(pkt, g_nl.cfg.user_ctx);
    return 0;
}

int eni_neuralink_calibrate(uint32_t duration_ms) {
    if (!g_nl.initialized || g_nl.state != ENI_NL_STATE_STREAMING) return -1;
    g_nl.state = ENI_NL_STATE_CALIBRATING;
    uint32_t samples = (g_nl.cfg.sample_rate * duration_ms) / 1000;
    if (samples == 0) samples = 100;
    /* Collect baseline — average over calibration period */
    memset(g_nl.calibration_baseline, 0, sizeof(g_nl.calibration_baseline));
    for (uint32_t s = 0; s < samples; s++) {
        eni_nl_packet_t pkt;
        g_nl.state = ENI_NL_STATE_STREAMING; /* Temporarily to read */
        eni_neuralink_read_packet(&pkt);
        for (uint32_t ch = 0; ch < pkt.channel_count; ch++)
            g_nl.calibration_baseline[ch] += pkt.channel_data[ch];
    }
    for (uint32_t ch = 0; ch < g_nl.cfg.channels && ch < ENI_NEURALINK_PACKET_SIZE; ch++)
        g_nl.calibration_baseline[ch] /= (float)samples;
    g_nl.calibrated = 1;
    g_nl.state = ENI_NL_STATE_STREAMING;
    return 0;
}

int eni_neuralink_set_threshold(float threshold) {
    if (!g_nl.initialized) return -1;
    g_nl.cfg.signal_threshold = threshold;
    return 0;
}

int eni_neuralink_decode_intent(const eni_nl_packet_t *pkt,
                                 char *intent, int maxlen, float *confidence) {
    if (!pkt || !intent || maxlen <= 0) return -1;
    /* Simple intent classification based on signal energy */
    float energy = 0;
    for (uint32_t ch = 0; ch < pkt->channel_count; ch++)
        energy += pkt->channel_data[ch] * pkt->channel_data[ch];
    energy = sqrtf(energy / (float)pkt->channel_count);

    float conf = 0;
    const char *decoded = "idle";
    if (energy > g_nl.cfg.signal_threshold * 4.0f) {
        decoded = "motor_execute";
        conf = 0.92f;
    } else if (energy > g_nl.cfg.signal_threshold * 2.0f) {
        decoded = "motor_intent";
        conf = 0.78f;
    } else if (energy > g_nl.cfg.signal_threshold) {
        decoded = "attention";
        conf = 0.65f;
    } else {
        decoded = "idle";
        conf = 0.95f;
    }
    strncpy(intent, decoded, (size_t)(maxlen - 1));
    intent[maxlen - 1] = '\0';
    if (confidence) *confidence = conf;
    if (g_nl.cfg.on_intent && conf > 0.5f)
        g_nl.cfg.on_intent(decoded, conf, g_nl.cfg.user_ctx);
    return 0;
}

int eni_neuralink_get_status(eni_nl_status_t *status) {
    if (!g_nl.initialized || !status) return -1;
    g_nl.status.state = g_nl.state;
    *status = g_nl.status;
    return 0;
}

eni_nl_state_t eni_neuralink_get_state(void) {
    return g_nl.state;
}

/* Provider integration - register as ENI provider */
static eni_status_t nl_prov_init(eni_provider_t *prov, const void *config) {
    (void)prov; (void)config; return ENI_OK;
}
static eni_status_t nl_prov_poll(eni_provider_t *prov, eni_event_t *ev) {
    (void)prov;
    if (!ev) return ENI_ERR_INVALID;
    eni_nl_packet_t pkt;
    if (eni_neuralink_read_packet(&pkt) != 0) return ENI_ERR_TIMEOUT;
    memset(ev, 0, sizeof(*ev));
    ev->type = ENI_EVENT_RAW;
    ev->timestamp.sec = pkt.timestamp_us / 1000000;
    ev->timestamp.nsec = (uint32_t)((pkt.timestamp_us % 1000000) * 1000);
    return ENI_OK;
}
static eni_status_t nl_prov_start(eni_provider_t *prov) { (void)prov; return ENI_OK; }
static eni_status_t nl_prov_stop(eni_provider_t *prov) { (void)prov; return ENI_OK; }
static void nl_prov_shutdown(eni_provider_t *prov) { (void)prov; eni_neuralink_deinit(); }
static const eni_provider_ops_t g_nl_provider = {
    .name = "neuralink",
    .init = nl_prov_init,
    .poll = nl_prov_poll,
    .start = nl_prov_start,
    .stop = nl_prov_stop,
    .shutdown = nl_prov_shutdown,
};
const eni_provider_ops_t *eni_neuralink_get_provider(void) {
    return &g_nl_provider;
}
