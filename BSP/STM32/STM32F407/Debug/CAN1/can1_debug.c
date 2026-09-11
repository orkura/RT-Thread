/*
 * Copyright (c) 2006-2026, RT-Thread Development Team
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <rtthread.h>
#include <rtdevice.h>
#include <finsh.h>

#define CAN1_DEBUG_DEVICE_NAME        "can1"
#define CAN1_DEBUG_DEFAULT_BAUD       CAN250kBaud
#define CAN1_DEBUG_DEFAULT_TIMEOUT_MS 1000U
#define CAN1_DEBUG_MAX_LOOP_COUNT     1000U
#define CAN1_DEBUG_MAX_TIMEOUT_MS     60000U
#define CAN1_DEBUG_MIN_BROADCAST_MS   10U
#define CAN1_DEBUG_MAX_BROADCAST_MS   60000U

enum can1_debug_command
{
    CAN1_DEBUG_CMD_HELP = 1,
    CAN1_DEBUG_CMD_OPEN,
    CAN1_DEBUG_CMD_CLOSE,
    CAN1_DEBUG_CMD_SEND,
    CAN1_DEBUG_CMD_RECV,
    CAN1_DEBUG_CMD_STATUS,
    CAN1_DEBUG_CMD_LOOPBACK,
    CAN1_DEBUG_CMD_BROADCAST,
    CAN1_DEBUG_CMD_BROADCAST_STATUS,
    CAN1_DEBUG_CMD_BROADCAST_STOP,
};

struct can1_debug_context
{
    rt_device_t device;
    struct rt_semaphore rx_sem;
    struct rt_mutex broadcast_lock;
    struct rt_timer broadcast_timer;
    struct rt_can_msg broadcast_message;
    rt_uint32_t broadcast_period_ms;
    rt_uint32_t broadcast_attempts;
    rt_uint32_t broadcast_queued;
    rt_uint32_t broadcast_failed;
    rt_bool_t sem_initialized;
    rt_bool_t broadcast_initialized;
    rt_bool_t broadcast_running;
    rt_bool_t opened;
};

static struct can1_debug_context can1_debug_ctx;

CMD_OPTIONS_STATEMENT(can1_debug)

static void can1_debug_usage(void)
{
    rt_kprintf("CAN1 debug command (default baud: 250000 bit/s)\n");
    rt_kprintf("Usage:\n");
    rt_kprintf("  can1 help\n");
    rt_kprintf("  can1 open [normal|loopback|listen|silent_loopback] [baud]\n");
    rt_kprintf("  can1 close\n");
    rt_kprintf("  can1 send <id> [byte0 ... byte7]\n");
    rt_kprintf("  can1 recv [timeout_ms]\n");
    rt_kprintf("  can1 status\n");
    rt_kprintf("  can1 loopback [count] [timeout_ms]\n");
    rt_kprintf("  can1 broadcast <id> <period_ms> [byte0 ... byte7]\n");
    rt_kprintf("  can1 broadcast_status\n");
    rt_kprintf("  can1 broadcast_stop\n");
    rt_kprintf("Baud: 1000000 800000 500000 250000 125000 100000 50000 20000 10000\n");
    rt_kprintf("ID accepts decimal or 0x-prefixed hex; data bytes are hexadecimal.\n");
    rt_kprintf("Broadcast period: 10..60000 ms; queued does not mean bus ACK.\n");
    rt_kprintf("Type 'can1 ' and press Tab to list or complete subcommands.\n");
}

static rt_err_t can1_debug_parse_uint(const char *text,
                                      rt_uint32_t base,
                                      rt_uint32_t maximum,
                                      rt_uint32_t *value)
{
    rt_uint32_t parsed = 0;
    rt_uint32_t digit;
    rt_bool_t has_digit = RT_FALSE;

    if (text == RT_NULL || value == RT_NULL || *text == '\0')
    {
        return -RT_EINVAL;
    }

    if (base == 0U)
    {
        if (text[0] == '0' && (text[1] == 'x' || text[1] == 'X'))
        {
            base = 16U;
            text += 2;
        }
        else
        {
            base = 10U;
        }
    }
    else if (base == 16U && text[0] == '0' &&
             (text[1] == 'x' || text[1] == 'X'))
    {
        text += 2;
    }

    while (*text != '\0')
    {
        if (*text >= '0' && *text <= '9')
        {
            digit = (rt_uint32_t)(*text - '0');
        }
        else if (*text >= 'a' && *text <= 'f')
        {
            digit = (rt_uint32_t)(*text - 'a') + 10U;
        }
        else if (*text >= 'A' && *text <= 'F')
        {
            digit = (rt_uint32_t)(*text - 'A') + 10U;
        }
        else
        {
            return -RT_EINVAL;
        }

        if (digit >= base || parsed > (maximum - digit) / base)
        {
            return -RT_EINVAL;
        }

        parsed = parsed * base + digit;
        has_digit = RT_TRUE;
        text++;
    }

    if (!has_digit)
    {
        return -RT_EINVAL;
    }

    *value = parsed;
    return RT_EOK;
}

static rt_bool_t can1_debug_baud_supported(rt_uint32_t baud)
{
    switch (baud)
    {
    case CAN1MBaud:
    case CAN800kBaud:
    case CAN500kBaud:
    case CAN250kBaud:
    case CAN125kBaud:
    case CAN100kBaud:
    case CAN50kBaud:
    case CAN20kBaud:
    case CAN10kBaud:
        return RT_TRUE;
    default:
        return RT_FALSE;
    }
}

static rt_err_t can1_debug_parse_mode(const char *text, rt_uint32_t *mode)
{
    if (rt_strcmp(text, "normal") == 0)
    {
        *mode = RT_CAN_MODE_NORMAL;
    }
    else if (rt_strcmp(text, "loopback") == 0)
    {
        *mode = RT_CAN_MODE_LOOPBACK;
    }
    else if (rt_strcmp(text, "listen") == 0)
    {
        *mode = RT_CAN_MODE_LISTEN;
    }
    else if (rt_strcmp(text, "silent_loopback") == 0)
    {
        *mode = RT_CAN_MODE_LOOPBACKANLISTEN;
    }
    else
    {
        return -RT_EINVAL;
    }

    return RT_EOK;
}

static const char *can1_debug_mode_name(rt_uint32_t mode)
{
    switch (mode)
    {
    case RT_CAN_MODE_NORMAL:
        return "normal";
    case RT_CAN_MODE_LISTEN:
        return "listen";
    case RT_CAN_MODE_LOOPBACK:
        return "loopback";
    case RT_CAN_MODE_LOOPBACKANLISTEN:
        return "silent_loopback";
    default:
        return "unknown";
    }
}

static rt_err_t can1_debug_rx_indicate(rt_device_t device, rt_size_t size)
{
    if (can1_debug_ctx.opened &&
        can1_debug_ctx.device == device &&
        size > 0U)
    {
        rt_sem_release(&can1_debug_ctx.rx_sem);
    }

    return RT_EOK;
}

static void can1_debug_broadcast_timeout(void *parameter)
{
    struct can1_debug_context *context = parameter;
    rt_ssize_t written;

    if (rt_mutex_take(&context->broadcast_lock, RT_WAITING_FOREVER) != RT_EOK)
    {
        return;
    }

    if (!context->broadcast_running ||
        !context->opened ||
        context->device == RT_NULL)
    {
        rt_mutex_release(&context->broadcast_lock);
        return;
    }

    context->broadcast_attempts++;
    written = rt_device_write(context->device,
                              0,
                              &context->broadcast_message,
                              sizeof(context->broadcast_message));
    if (written == (rt_ssize_t)sizeof(context->broadcast_message))
    {
        context->broadcast_queued++;
    }
    else
    {
        context->broadcast_failed++;
    }

    rt_mutex_release(&context->broadcast_lock);
}

static rt_err_t can1_debug_prepare_resources(void)
{
    rt_err_t result;

    if (!can1_debug_ctx.sem_initialized)
    {
        result = rt_sem_init(&can1_debug_ctx.rx_sem,
                             "c1dbg_rx",
                             0,
                             RT_IPC_FLAG_FIFO);
        if (result != RT_EOK)
        {
            return result;
        }
        can1_debug_ctx.sem_initialized = RT_TRUE;
    }

    if (!can1_debug_ctx.broadcast_initialized)
    {
        result = rt_mutex_init(&can1_debug_ctx.broadcast_lock,
                               "c1dbg_tx",
                               RT_IPC_FLAG_PRIO);
        if (result != RT_EOK)
        {
            return result;
        }

        rt_timer_init(&can1_debug_ctx.broadcast_timer,
                      "c1dbg_tx",
                      can1_debug_broadcast_timeout,
                      &can1_debug_ctx,
                      1,
                      RT_TIMER_FLAG_PERIODIC | RT_TIMER_FLAG_SOFT_TIMER);
        can1_debug_ctx.broadcast_initialized = RT_TRUE;
    }

    return RT_EOK;
}

static void can1_debug_drain_rx_signal(void)
{
    while (rt_sem_take(&can1_debug_ctx.rx_sem, 0) == RT_EOK)
    {
        /* Drain stale receive indications before starting a new test. */
    }
}

static rt_err_t can1_debug_stop_broadcast(rt_bool_t verbose)
{
    rt_uint32_t attempts;
    rt_uint32_t queued;
    rt_uint32_t failed;
    rt_err_t result;

    if (!can1_debug_ctx.broadcast_initialized)
    {
        if (verbose)
        {
            rt_kprintf("CAN1 broadcast is not running\n");
        }
        return RT_EOK;
    }

    result = rt_mutex_take(&can1_debug_ctx.broadcast_lock,
                           RT_WAITING_FOREVER);
    if (result != RT_EOK)
    {
        return result;
    }

    if (!can1_debug_ctx.broadcast_running)
    {
        rt_mutex_release(&can1_debug_ctx.broadcast_lock);
        if (verbose)
        {
            rt_kprintf("CAN1 broadcast is not running\n");
        }
        return RT_EOK;
    }

    can1_debug_ctx.broadcast_running = RT_FALSE;
    result = rt_timer_stop(&can1_debug_ctx.broadcast_timer);
    attempts = can1_debug_ctx.broadcast_attempts;
    queued = can1_debug_ctx.broadcast_queued;
    failed = can1_debug_ctx.broadcast_failed;
    rt_mutex_release(&can1_debug_ctx.broadcast_lock);

    if (verbose)
    {
        rt_kprintf("CAN1 broadcast stopped: attempts=%u queued=%u local_fail=%u\n",
                   (unsigned int)attempts,
                   (unsigned int)queued,
                   (unsigned int)failed);
    }

    return result;
}

static rt_err_t can1_debug_open_device(rt_uint32_t mode,
                                       rt_uint32_t baud,
                                       rt_bool_t verbose)
{
    rt_device_t device;
    rt_err_t result;

    if (can1_debug_ctx.opened)
    {
        rt_kprintf("can1 is already opened by this debug command\n");
        return -RT_EBUSY;
    }

    device = rt_device_find(CAN1_DEBUG_DEVICE_NAME);
    if (device == RT_NULL)
    {
        rt_kprintf("can1 device was not found\n");
        return -RT_ENOSYS;
    }

    if (device->ref_count != 0U)
    {
        rt_kprintf("can1 is busy (reference count: %u)\n",
                   (unsigned int)device->ref_count);
        return -RT_EBUSY;
    }

    result = can1_debug_prepare_resources();
    if (result != RT_EOK)
    {
        rt_kprintf("can1 debug resource initialization failed: %d\n", result);
        return result;
    }
    can1_debug_drain_rx_signal();

    result = rt_device_control(device,
                               RT_CAN_CMD_SET_BAUD,
                               (void *)(rt_ubase_t)baud);
    if (result != RT_EOK)
    {
        rt_kprintf("can1 baud configuration failed: %d\n", result);
        return result;
    }

    result = rt_device_control(device,
                               RT_CAN_CMD_SET_MODE,
                               (void *)(rt_ubase_t)mode);
    if (result != RT_EOK)
    {
        rt_kprintf("can1 mode configuration failed: %d\n", result);
        return result;
    }

    result = rt_device_open(device,
                            RT_DEVICE_FLAG_INT_RX | RT_DEVICE_FLAG_INT_TX);
    if (result != RT_EOK)
    {
        rt_kprintf("can1 open failed: %d\n", result);
        return result;
    }

    can1_debug_ctx.device = device;
    can1_debug_ctx.opened = RT_TRUE;
    rt_device_set_rx_indicate(device, can1_debug_rx_indicate);

    result = rt_device_control(device,
                               RT_CAN_CMD_START,
                               (void *)(rt_ubase_t)RT_TRUE);
    if (result != RT_EOK)
    {
        rt_device_set_rx_indicate(device, RT_NULL);
        can1_debug_ctx.opened = RT_FALSE;
        can1_debug_ctx.device = RT_NULL;
        rt_device_close(device);
        rt_kprintf("can1 start failed: %d\n", result);
        return result;
    }

    if (verbose)
    {
        rt_kprintf("can1 opened: mode=%s baud=%u\n",
                   can1_debug_mode_name(mode),
                   (unsigned int)baud);
    }

    return RT_EOK;
}

static rt_err_t can1_debug_close_device(rt_bool_t verbose)
{
    rt_device_t device;
    rt_err_t stop_result;
    rt_err_t close_result;

    if (!can1_debug_ctx.opened || can1_debug_ctx.device == RT_NULL)
    {
        if (verbose)
        {
            rt_kprintf("can1 is not opened by this debug command\n");
        }
        return -RT_ERROR;
    }

    can1_debug_stop_broadcast(RT_FALSE);
    device = can1_debug_ctx.device;
    stop_result = rt_device_control(device,
                                    RT_CAN_CMD_START,
                                    (void *)(rt_ubase_t)RT_FALSE);
    rt_device_set_rx_indicate(device, RT_NULL);
    can1_debug_ctx.opened = RT_FALSE;
    can1_debug_ctx.device = RT_NULL;
    close_result = rt_device_close(device);

    if (verbose)
    {
        if (stop_result == RT_EOK && close_result == RT_EOK)
        {
            rt_kprintf("can1 closed\n");
        }
        else
        {
            rt_kprintf("can1 close failed: stop=%d close=%d\n",
                       stop_result,
                       close_result);
        }
    }

    return stop_result != RT_EOK ? stop_result : close_result;
}

static void can1_debug_print_frame(const char *prefix,
                                   const struct rt_can_msg *message)
{
    rt_uint32_t index;

    rt_kprintf("%s id=0x%08x type=%s len=%u data=",
               prefix,
               (unsigned int)message->id,
               message->ide == RT_CAN_EXTID ? "EXT" : "STD",
               (unsigned int)message->len);
    for (index = 0; index < message->len; index++)
    {
        rt_kprintf("%02x%s",
                   message->data[index],
                   index + 1U == message->len ? "" : " ");
    }
    rt_kprintf("\n");
}

static int can1_debug_open_command(int argc, char **argv)
{
    rt_uint32_t mode = RT_CAN_MODE_NORMAL;
    rt_uint32_t baud = CAN1_DEBUG_DEFAULT_BAUD;

    if (argc < 2 || argc > 4)
    {
        rt_kprintf("Usage: can1 open [normal|loopback|listen|silent_loopback] [baud]\n");
        return -RT_EINVAL;
    }

    if (argc >= 3 && can1_debug_parse_mode(argv[2], &mode) != RT_EOK)
    {
        rt_kprintf("Invalid mode: %s\n", argv[2]);
        rt_kprintf("Modes: normal loopback listen silent_loopback\n");
        return -RT_EINVAL;
    }

    if (argc == 4 &&
        (can1_debug_parse_uint(argv[3], 10U, CAN1MBaud, &baud) != RT_EOK ||
         !can1_debug_baud_supported(baud)))
    {
        rt_kprintf("Unsupported baud: %s\n", argv[3]);
        rt_kprintf("Baud: 1000000 800000 500000 250000 125000 100000 50000 20000 10000\n");
        return -RT_EINVAL;
    }

    return can1_debug_open_device(mode, baud, RT_TRUE);
}

static int can1_debug_send_command(int argc, char **argv)
{
    struct rt_can_msg message = {0};
    rt_uint32_t value;
    int index;
    rt_ssize_t written;

    if (!can1_debug_ctx.opened || can1_debug_ctx.device == RT_NULL)
    {
        rt_kprintf("Open can1 first: can1 open normal 250000\n");
        return -RT_ERROR;
    }

    if (argc < 3 || argc > 11)
    {
        rt_kprintf("Usage: can1 send <id> [byte0 ... byte7]\n");
        rt_kprintf("Example: can1 send 0x123 11 22 AA 55\n");
        return -RT_EINVAL;
    }

    if (can1_debug_parse_uint(argv[2], 0U, 0x1FFFFFFFU, &value) != RT_EOK)
    {
        rt_kprintf("Invalid CAN ID: %s\n", argv[2]);
        return -RT_EINVAL;
    }

    message.id = value;
    message.ide = value <= 0x7FFU ? RT_CAN_STDID : RT_CAN_EXTID;
    message.rtr = RT_CAN_DTR;
    message.len = (rt_uint32_t)(argc - 3);
    message.hdr_index = -1;

    for (index = 3; index < argc; index++)
    {
        if (can1_debug_parse_uint(argv[index], 16U, 0xFFU, &value) != RT_EOK)
        {
            rt_kprintf("Invalid data byte: %s\n", argv[index]);
            return -RT_EINVAL;
        }
        message.data[index - 3] = (rt_uint8_t)value;
    }

    written = rt_device_write(can1_debug_ctx.device,
                              0,
                              &message,
                              sizeof(message));
    if (written != (rt_ssize_t)sizeof(message))
    {
        rt_kprintf("can1 send failed: %d\n", (int)written);
        return -RT_ERROR;
    }

    can1_debug_print_frame("TX", &message);
    return RT_EOK;
}

static int can1_debug_broadcast_command(int argc, char **argv)
{
    struct rt_can_device *can;
    struct rt_can_msg message = {0};
    rt_uint32_t period_ms;
    rt_uint32_t value;
    rt_tick_t period_tick;
    rt_err_t result;
    int index;

    if (!can1_debug_ctx.opened || can1_debug_ctx.device == RT_NULL)
    {
        rt_kprintf("Open can1 first: can1 open normal 250000\n");
        return -RT_ERROR;
    }

    can = (struct rt_can_device *)can1_debug_ctx.device;
    if (can->config.mode != RT_CAN_MODE_NORMAL)
    {
        rt_kprintf("CAN1 broadcast requires normal mode (current: %s)\n",
                   can1_debug_mode_name(can->config.mode));
        return -RT_EINVAL;
    }

    if (argc < 4 || argc > 12)
    {
        rt_kprintf("Usage: can1 broadcast <id> <period_ms> [byte0 ... byte7]\n");
        rt_kprintf("Example: can1 broadcast 0x123 100 11 22 33 44\n");
        return -RT_EINVAL;
    }

    if (can1_debug_parse_uint(argv[2], 0U, 0x1FFFFFFFU, &value) != RT_EOK)
    {
        rt_kprintf("Invalid CAN ID: %s\n", argv[2]);
        return -RT_EINVAL;
    }

    message.id = value;
    message.ide = value <= 0x7FFU ? RT_CAN_STDID : RT_CAN_EXTID;
    message.rtr = RT_CAN_DTR;
    message.len = (rt_uint32_t)(argc - 4);
    message.hdr_index = -1;
    message.nonblocking = 1;

    if (can1_debug_parse_uint(argv[3],
                              10U,
                              CAN1_DEBUG_MAX_BROADCAST_MS,
                              &period_ms) != RT_EOK ||
        period_ms < CAN1_DEBUG_MIN_BROADCAST_MS)
    {
        rt_kprintf("Invalid broadcast period: %s (range: 10..60000 ms)\n",
                   argv[3]);
        return -RT_EINVAL;
    }

    for (index = 4; index < argc; index++)
    {
        if (can1_debug_parse_uint(argv[index], 16U, 0xFFU, &value) != RT_EOK)
        {
            rt_kprintf("Invalid data byte: %s\n", argv[index]);
            return -RT_EINVAL;
        }
        message.data[index - 4] = (rt_uint8_t)value;
    }

    result = rt_mutex_take(&can1_debug_ctx.broadcast_lock,
                           RT_WAITING_FOREVER);
    if (result != RT_EOK)
    {
        return result;
    }

    if (can1_debug_ctx.broadcast_running)
    {
        rt_mutex_release(&can1_debug_ctx.broadcast_lock);
        rt_kprintf("CAN1 broadcast is already running; stop it first\n");
        return -RT_EBUSY;
    }

    can1_debug_ctx.broadcast_message = message;
    can1_debug_ctx.broadcast_period_ms = period_ms;
    can1_debug_ctx.broadcast_attempts = 0U;
    can1_debug_ctx.broadcast_queued = 0U;
    can1_debug_ctx.broadcast_failed = 0U;
    period_tick = rt_tick_from_millisecond((rt_int32_t)period_ms);
    result = rt_timer_control(&can1_debug_ctx.broadcast_timer,
                              RT_TIMER_CTRL_SET_TIME,
                              &period_tick);
    if (result == RT_EOK)
    {
        can1_debug_ctx.broadcast_running = RT_TRUE;
        result = rt_timer_start(&can1_debug_ctx.broadcast_timer);
        if (result != RT_EOK)
        {
            can1_debug_ctx.broadcast_running = RT_FALSE;
        }
    }
    rt_mutex_release(&can1_debug_ctx.broadcast_lock);

    if (result != RT_EOK)
    {
        rt_kprintf("CAN1 broadcast start failed: %d\n", result);
        return result;
    }

    rt_kprintf("CAN1 broadcast started: period=%u ms (non-blocking)\n",
               (unsigned int)period_ms);
    can1_debug_print_frame("Broadcast", &message);
    rt_kprintf("Use 'can1 broadcast_status'; queued frames are not proof of ACK.\n");
    return RT_EOK;
}

static int can1_debug_broadcast_status_command(int argc, char **argv)
{
    struct rt_can_msg message = {0};
    struct rt_can_status status = {0};
    rt_uint32_t period_ms = 0U;
    rt_uint32_t attempts = 0U;
    rt_uint32_t queued = 0U;
    rt_uint32_t failed = 0U;
    rt_bool_t running = RT_FALSE;
    rt_err_t result;

    if (argc != 2)
    {
        rt_kprintf("Usage: can1 broadcast_status\n");
        return -RT_EINVAL;
    }

    if (can1_debug_ctx.broadcast_initialized)
    {
        result = rt_mutex_take(&can1_debug_ctx.broadcast_lock,
                               RT_WAITING_FOREVER);
        if (result != RT_EOK)
        {
            return result;
        }
        running = can1_debug_ctx.broadcast_running;
        message = can1_debug_ctx.broadcast_message;
        period_ms = can1_debug_ctx.broadcast_period_ms;
        attempts = can1_debug_ctx.broadcast_attempts;
        queued = can1_debug_ctx.broadcast_queued;
        failed = can1_debug_ctx.broadcast_failed;
        rt_mutex_release(&can1_debug_ctx.broadcast_lock);
    }

    rt_kprintf("CAN1 broadcast: running=%u period=%u ms attempts=%u queued=%u local_fail=%u\n",
               (unsigned int)running,
               (unsigned int)period_ms,
               (unsigned int)attempts,
               (unsigned int)queued,
               (unsigned int)failed);
    if (period_ms != 0U)
    {
        can1_debug_print_frame("Broadcast", &message);
    }

    if (can1_debug_ctx.opened && can1_debug_ctx.device != RT_NULL)
    {
        result = rt_device_control(can1_debug_ctx.device,
                                   RT_CAN_CMD_GET_STATUS,
                                   &status);
        if (result == RT_EOK)
        {
            rt_kprintf("CAN status: tx=%u tx_drop=%u REC=%u TEC=%u err=%u\n",
                       (unsigned int)status.sndpkg,
                       (unsigned int)status.dropedsndpkg,
                       (unsigned int)status.rcverrcnt,
                       (unsigned int)status.snderrcnt,
                       (unsigned int)status.errcode);
        }
        else
        {
            rt_kprintf("CAN status read failed: %d\n", result);
            return result;
        }
    }

    rt_kprintf("queued only means accepted by the driver/software queue, not bus ACK.\n");
    return RT_EOK;
}

static int can1_debug_recv_command(int argc, char **argv)
{
    struct rt_can_msg message = {0};
    rt_uint32_t timeout_ms = CAN1_DEBUG_DEFAULT_TIMEOUT_MS;
    rt_err_t result;
    rt_ssize_t received;

    if (!can1_debug_ctx.opened || can1_debug_ctx.device == RT_NULL)
    {
        rt_kprintf("Open can1 first: can1 open normal 250000\n");
        return -RT_ERROR;
    }

    if (argc > 3 ||
        (argc == 3 &&
         can1_debug_parse_uint(argv[2], 10U,
                               CAN1_DEBUG_MAX_TIMEOUT_MS,
                               &timeout_ms) != RT_EOK))
    {
        rt_kprintf("Usage: can1 recv [timeout_ms]\n");
        return -RT_EINVAL;
    }

    result = rt_sem_take(&can1_debug_ctx.rx_sem,
                         rt_tick_from_millisecond((rt_int32_t)timeout_ms));
    if (result != RT_EOK)
    {
        rt_kprintf("can1 receive timeout after %u ms\n",
                   (unsigned int)timeout_ms);
        return result;
    }

    message.hdr_index = -1;
    received = rt_device_read(can1_debug_ctx.device,
                              0,
                              &message,
                              sizeof(message));
    if (received != (rt_ssize_t)sizeof(message))
    {
        rt_kprintf("can1 receive failed: %d\n", (int)received);
        return -RT_ERROR;
    }

    can1_debug_print_frame("RX", &message);
    return RT_EOK;
}

static int can1_debug_status_command(int argc, char **argv)
{
    rt_device_t device;
    struct rt_can_device *can;
    struct rt_can_status status = {0};
    rt_err_t result = RT_EOK;

    if (argc != 2)
    {
        rt_kprintf("Usage: can1 status\n");
        return -RT_EINVAL;
    }

    device = rt_device_find(CAN1_DEBUG_DEVICE_NAME);
    if (device == RT_NULL)
    {
        rt_kprintf("can1 device was not found\n");
        return -RT_ENOSYS;
    }

    can = (struct rt_can_device *)device;
    if (device->flag & RT_DEVICE_FLAG_ACTIVATED)
    {
        result = rt_device_control(device, RT_CAN_CMD_GET_STATUS, &status);
    }

    rt_kprintf("can1: active=%u debug_open=%u refs=%u flags=0x%04x\n",
               (unsigned int)((device->flag & RT_DEVICE_FLAG_ACTIVATED) != 0U),
               (unsigned int)can1_debug_ctx.opened,
               (unsigned int)device->ref_count,
               (unsigned int)device->open_flag);
    rt_kprintf("config: mode=%s baud=%u rx_box=%u tx_box=%u\n",
               can1_debug_mode_name(can->config.mode),
               (unsigned int)can->config.baud_rate,
               (unsigned int)can->config.msgboxsz,
               (unsigned int)can->config.sndboxnumber);
    rt_kprintf("status: rx=%u rx_drop=%u tx=%u tx_drop=%u REC=%u TEC=%u err=%u\n",
               (unsigned int)status.rcvpkg,
               (unsigned int)status.dropedrcvpkg,
               (unsigned int)status.sndpkg,
               (unsigned int)status.dropedsndpkg,
               (unsigned int)status.rcverrcnt,
               (unsigned int)status.snderrcnt,
               (unsigned int)status.errcode);

    return result;
}

static int can1_debug_loopback_command(int argc, char **argv)
{
    rt_device_t device;
    struct rt_can_msg tx_message;
    struct rt_can_msg rx_message;
    rt_uint32_t count = 1U;
    rt_uint32_t timeout_ms = CAN1_DEBUG_DEFAULT_TIMEOUT_MS;
    rt_uint32_t index;
    rt_uint32_t byte_index;
    rt_uint32_t passed = 0U;
    rt_err_t result;
    rt_err_t close_result;
    rt_err_t restore_result;
    rt_ssize_t transferred;

    if (argc > 4 ||
        (argc >= 3 &&
         can1_debug_parse_uint(argv[2], 10U,
                               CAN1_DEBUG_MAX_LOOP_COUNT,
                               &count) != RT_EOK) ||
        count == 0U ||
        (argc == 4 &&
         can1_debug_parse_uint(argv[3], 10U,
                               CAN1_DEBUG_MAX_TIMEOUT_MS,
                               &timeout_ms) != RT_EOK) ||
        timeout_ms == 0U)
    {
        rt_kprintf("Usage: can1 loopback [count:1..1000] [timeout_ms:1..60000]\n");
        return -RT_EINVAL;
    }

    if (can1_debug_ctx.opened)
    {
        rt_kprintf("Close the current debug session before loopback testing\n");
        return -RT_EBUSY;
    }

    device = rt_device_find(CAN1_DEBUG_DEVICE_NAME);
    result = can1_debug_open_device(RT_CAN_MODE_LOOPBACK,
                                    CAN1_DEBUG_DEFAULT_BAUD,
                                    RT_FALSE);
    if (result != RT_EOK)
    {
        return result;
    }

    rt_kprintf("CAN1 internal loopback: count=%u timeout=%u ms baud=%u\n",
               (unsigned int)count,
               (unsigned int)timeout_ms,
               (unsigned int)CAN1_DEBUG_DEFAULT_BAUD);

    for (index = 0; index < count; index++)
    {
        rt_memset(&tx_message, 0, sizeof(tx_message));
        rt_memset(&rx_message, 0, sizeof(rx_message));

        tx_message.id = 0x120U + (index & 0x7FU);
        tx_message.ide = RT_CAN_STDID;
        tx_message.rtr = RT_CAN_DTR;
        tx_message.len = 8U;
        tx_message.hdr_index = -1;
        for (byte_index = 0; byte_index < tx_message.len; byte_index++)
        {
            tx_message.data[byte_index] =
                (rt_uint8_t)((index + byte_index) & 0xFFU);
        }

        transferred = rt_device_write(can1_debug_ctx.device,
                                      0,
                                      &tx_message,
                                      sizeof(tx_message));
        if (transferred != (rt_ssize_t)sizeof(tx_message))
        {
            rt_kprintf("Loopback TX failed at frame %u: %d\n",
                       (unsigned int)index,
                       (int)transferred);
            result = -RT_ERROR;
            break;
        }

        result = rt_sem_take(&can1_debug_ctx.rx_sem,
                             rt_tick_from_millisecond((rt_int32_t)timeout_ms));
        if (result != RT_EOK)
        {
            rt_kprintf("Loopback RX timeout at frame %u\n",
                       (unsigned int)index);
            break;
        }

        rx_message.hdr_index = -1;
        transferred = rt_device_read(can1_debug_ctx.device,
                                     0,
                                     &rx_message,
                                     sizeof(rx_message));
        if (transferred != (rt_ssize_t)sizeof(rx_message))
        {
            rt_kprintf("Loopback RX failed at frame %u: %d\n",
                       (unsigned int)index,
                       (int)transferred);
            result = -RT_ERROR;
            break;
        }

        if (rx_message.id != tx_message.id ||
            rx_message.ide != tx_message.ide ||
            rx_message.rtr != tx_message.rtr ||
            rx_message.len != tx_message.len ||
            rt_memcmp(rx_message.data,
                      tx_message.data,
                      tx_message.len) != 0)
        {
            rt_kprintf("Loopback data mismatch at frame %u\n",
                       (unsigned int)index);
            can1_debug_print_frame("TX", &tx_message);
            can1_debug_print_frame("RX", &rx_message);
            result = -RT_ERROR;
            break;
        }

        passed++;
        result = RT_EOK;
    }

    close_result = can1_debug_close_device(RT_FALSE);
    restore_result = rt_device_control(device,
                                       RT_CAN_CMD_SET_MODE,
                                       (void *)(rt_ubase_t)RT_CAN_MODE_NORMAL);

    if (result == RT_EOK && close_result != RT_EOK)
    {
        result = close_result;
    }
    if (result == RT_EOK && restore_result != RT_EOK)
    {
        result = restore_result;
    }

    if (result == RT_EOK && passed == count)
    {
        rt_kprintf("CAN1 loopback PASS: %u/%u frames\n",
                   (unsigned int)passed,
                   (unsigned int)count);
    }
    else
    {
        rt_kprintf("CAN1 loopback FAIL: %u/%u frames, error=%d\n",
                   (unsigned int)passed,
                   (unsigned int)count,
                   result);
    }

    return result;
}

static int can1_debug(int argc, char **argv)
{
    if (argc < 2)
    {
        can1_debug_usage();
        return -RT_EINVAL;
    }

    switch (MSH_OPT_ID_GET(can1_debug))
    {
    case CAN1_DEBUG_CMD_HELP:
        can1_debug_usage();
        return RT_EOK;
    case CAN1_DEBUG_CMD_OPEN:
        return can1_debug_open_command(argc, argv);
    case CAN1_DEBUG_CMD_CLOSE:
        if (argc != 2)
        {
            rt_kprintf("Usage: can1 close\n");
            return -RT_EINVAL;
        }
        return can1_debug_close_device(RT_TRUE);
    case CAN1_DEBUG_CMD_SEND:
        return can1_debug_send_command(argc, argv);
    case CAN1_DEBUG_CMD_RECV:
        return can1_debug_recv_command(argc, argv);
    case CAN1_DEBUG_CMD_STATUS:
        return can1_debug_status_command(argc, argv);
    case CAN1_DEBUG_CMD_LOOPBACK:
        return can1_debug_loopback_command(argc, argv);
    case CAN1_DEBUG_CMD_BROADCAST:
        return can1_debug_broadcast_command(argc, argv);
    case CAN1_DEBUG_CMD_BROADCAST_STATUS:
        return can1_debug_broadcast_status_command(argc, argv);
    case CAN1_DEBUG_CMD_BROADCAST_STOP:
        if (argc != 2)
        {
            rt_kprintf("Usage: can1 broadcast_stop\n");
            return -RT_EINVAL;
        }
        return can1_debug_stop_broadcast(RT_TRUE);
    default:
        rt_kprintf("Unknown CAN1 subcommand: %s\n", argv[1]);
        can1_debug_usage();
        return -RT_EINVAL;
    }
}

CMD_OPTIONS_NODE_START(can1_debug)
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_HELP, help, show usage and parameter hints)
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_OPEN, open, open [mode] [baud])
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_CLOSE, close, stop and close CAN1)
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_SEND, send, send <id> [byte0 ... byte7])
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_RECV, recv, recv [timeout_ms])
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_STATUS, status, show configuration and counters)
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_LOOPBACK, loopback, loopback [count] [timeout_ms])
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_BROADCAST, broadcast, broadcast <id> <period_ms> [byte0 ... byte7])
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_BROADCAST_STATUS, broadcast_status, show periodic broadcast counters)
CMD_OPTIONS_NODE(CAN1_DEBUG_CMD_BROADCAST_STOP, broadcast_stop, stop periodic broadcast)
CMD_OPTIONS_NODE_END

MSH_CMD_EXPORT_ALIAS(can1_debug,
                     can1,
                     CAN1 interactive debug and internal loopback test,
                     optenable);
