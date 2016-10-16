/**
 * @file inet/network_interface/wifi.h
 *
 * @section License
 * Copyright (C) 2016, Erik Moqvist
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERSOCKTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * This file is part of the Simba project.
 */

#ifndef __INET_NETWORK_INTERFACE_WIFI_H__
#define __INET_NETWORK_INTERFACE_WIFI_H__

#include "simba.h"

/**
 * Driver virtualization callbacks.
 */
struct network_interface_wifi_driver_t {
    int (*init)(void *arg_p,
                const char *ssid_p,
                const char *password_p,
                struct inet_if_ip_info_t *info_p);
    int (*start)(void *arg_p);
    int (*stop)(void *arg_p);
    int (*is_up)(void *arg_p);
    int (*set_ip_info)(void *arg_p, const struct inet_if_ip_info_t *info_p);
    int (*get_ip_info)(void *arg_p, struct inet_if_ip_info_t *info_p);
};

/**
 * A WiFi network interface.
 */
struct network_interface_wifi_t {
    struct network_interface_t network_interface;
    struct network_interface_wifi_driver_t *driver_p;
    void *arg_p;
};

/**
 * Initialize the WiFi network interface module.
 *
 * @return zero(0) or negative error code.
 */
int network_interface_wifi_module_init(void);

/**
 * Initialize given WiFi network interface with given configuration.
 *
 * @param[in] ssid_p Access Point SSID.
 * @param[in] password_p Access Point password.
 *
 * @return zero(0) or negative error code.
 */
int network_interface_wifi_init(struct network_interface_wifi_t *self_p,
                                const char *name_p,
                                struct network_interface_wifi_driver_t *driver_p,
                                void *arg_p,
                                const char *ssid_p,
                                const char *password_p);

/**
 * Start given WiFi network interface.
 *
 * @return zero(0) or negative error code.
 */
int network_interface_wifi_start(struct network_interface_wifi_t *self_p);

/**
 * Stop given WiFi network interface.
 *
 * @return zero(0) or negative error code.
 */
int network_interface_wifi_stop(struct network_interface_wifi_t *self_p);

/**
 * Get the connection status of given network interface.
 *
 * @param[in] self_p Network interface to get the connection status
 *                   of.
 *
 * @return true(1) if the network interface is up, false(0) is it is
 *         down, and otherwise negative error code.
 */
int network_interface_wifi_is_up(struct network_interface_wifi_t *self_p);

/**
 * Set the ip address, netmask and gateway of given network interface.
 *
 * @param[in] self_p Network interface.
 * @param[in] info_p Interface IP information to set.
 *
 * @return zero(0) if the interface has valid IP information,
 *         otherwise negative error code.
 */
int network_interface_wifi_set_ip_info(struct network_interface_wifi_t *self_p,
                                       const struct inet_if_ip_info_t *info_p);

/**
 * Get the ip address, netmask and gateway of given network interface.
 *
 * @param[in] self_p Network interface.
 * @param[out] info_p Interface IP information. Only valid if this
 *                    function returns zero(0).
 *
 * @return zero(0) if the interface has valid IP information,
 *         otherwise negative error code.
 */
int network_interface_wifi_get_ip_info(struct network_interface_wifi_t *self_p,
                                       struct inet_if_ip_info_t *info_p);

#endif