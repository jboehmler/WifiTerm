/**
 * @file batmon.h
 * @brief Battery voltage from A0 (ESP8266 TOUT pin, 0..1 V, 10-bit). See battery.h.
 */
#ifndef BATMON_H
#define BATMON_H

/** @brief Set up the ADC. @return 0 on success. */
int batmon_init(void);

/** @brief Use a calibration (`bat cal`). @param cal Per mille, BAT_CAL_MIN..BAT_CAL_MAX. */
void batmon_set_cal(int cal);

/** @brief Calibration in use. @return Per mille. */
int batmon_cal(void);

/** @brief Battery voltage now, calibrated (average of a few readings). @return mV, or 0 if the ADC failed. */
int batmon_read_mv(void);

#endif /* BATMON_H */
