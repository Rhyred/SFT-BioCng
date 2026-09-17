#pragma once

/**
 * @file PinDefinitions.h
 * @brief Pin Mapping for NICEGAS Bio-CNG IoT Nodes based on Hardware Schematic
 */

// ==============================================================================
// NODE 1: BIODIGESTER PINOUT (Active Node)
// ==============================================================================
#define PIN_BIODIGESTER_TEMP_ONEWIRE   2   // D4 (GPIO2) -> DS18B20 Temperature Data
#define PIN_BIODIGESTER_CH4_ANALOG    34   // A0 (GPIO34 / ADC1_CH6) -> MQ-4 CH4 Analog
#define PIN_BIODIGESTER_PH_ANALOG     35   // A1 (GPIO35 / ADC1_CH7) -> pH-4502C Analog

// ==============================================================================
// NODE 2: PURIFIKASI PINOUT (For Future Expansion)
// ==============================================================================
#define PIN_PURIFIKASI_H2S_ANALOG     34   // A0 (GPIO34) -> MQ-136 H2S
#define PIN_PURIFIKASI_CO2_ANALOG     35   // A1 (GPIO35) -> MQ-135 CO2

// ==============================================================================
// NODE 3: KOMPRESI PINOUT (For Future Expansion)
// ==============================================================================
#define PIN_KOMPRESI_CH4_ANALOG       34   // A0 (GPIO34) -> MQ-4 CH4
#define PIN_KOMPRESI_PRESS_ANALOG     35   // A1 (GPIO35) -> Pressure Transducer 0-10 MPa

// ==============================================================================
// NODE 4: AKTUASI PINOUT (For Future Expansion)
// ==============================================================================
#define PIN_AKTUASI_SOLENOID_VALVE    14   // D5 (GPIO14) -> Solenoid Valve Gas
#define PIN_AKTUASI_RELAY_CH1         18   // D18 (GPIO18) -> Relay Channel 1
#define PIN_AKTUASI_RELAY_CH2         19   // D19 (GPIO19) -> Relay Channel 2
#define PIN_AKTUASI_RELAY_CH3         21   // D21 (GPIO21) -> Relay Channel 3
#define PIN_AKTUASI_RELAY_CH4         22   // D22 (GPIO22) -> Relay Channel 4
