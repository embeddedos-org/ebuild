/**
 * @file app_config.h
 * @brief Cortex-R5 safety demo — project configuration
 */

#ifndef APP_CONFIG_H
#define APP_CONFIG_H

/* ---- SCI (UART) ---- */
#define APP_SCI_BASE            0xFFF7E400
#define APP_SCI_BAUD            115200

/* ---- RTI timer ---- */
#define APP_RTI_BASE            0xFFFFFC00
#define APP_RTI_TICK_HZ         1000
#define APP_CPU_HZ              300000000

/* ---- DWD watchdog ---- */
#define APP_WDT_TIMEOUT_MS      100
#define APP_WDT_PRELOAD         0x00002710

/* ---- DCAN (heartbeat) ---- */
#define APP_DCAN_BASE           0xFFF7DC00
#define APP_CAN_NODE_ID         0x42
#define APP_HEARTBEAT_INTERVAL  1000

/* ---- ESM (Error Signaling Module) ---- */
#define APP_ESM_BASE            0xFFFFF500
#define APP_ESM_ECC_CHANNEL     2

/* ---- Safety ---- */
#define APP_ECC_CHECK_ENABLE    1
#define APP_LOCKSTEP_MODE       1

/* ---- GPIO ---- */
#define APP_LED_PORT_BASE       0xFFF7BC00
#define APP_LED_BIT             0

#endif /* APP_CONFIG_H */
