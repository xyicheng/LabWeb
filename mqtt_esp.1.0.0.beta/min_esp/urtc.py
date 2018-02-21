import ucollections
import utime
DateTimeTuple = ucollections.namedtuple("DateTimeTuple", ["year", "month",
    "day", "weekday", "hour", "minute", "second", "millisecond"])
def datetime_tuple(year=None, month=None, day=None, weekday=None, hour=None,
                   minute=None, second=None, millisecond=None):
    return DateTimeTuple(year, month, day, weekday, hour, minute,
                         second, millisecond)
def _bcd2bin(value):
    return (value or 0) - 6 * ((value or 0) >> 4)
def _bin2bcd(value):
    return (value or 0) + 6 * ((value or 0) // 10)
def tuple2seconds(datetime):
    return utime.mktime((datetime.year, datetime.month, datetime.day,
        datetime.hour, datetime.minute, datetime.second, datetime.weekday, 0))
def seconds2tuple(seconds):
    (year, month, day, hour, minute,
     second, weekday, _yday) = utime.localtime(seconds)
    return DateTimeTuple(year, month, day, weekday, hour, minute, second, 0)
class _BaseRTC:
    _SWAP_DAY_WEEKDAY = False
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.address = address
    def _register(self, register, buffer=None):
        if buffer is None:
            return self.i2c.readfrom_mem(self.address, register, 1)[0]
        self.i2c.writeto_mem(self.address, register, buffer)
    def _flag(self, register, mask, value=None):
        data = self._register(register)
        if value is None:
            return bool(data & mask)
        if value:
            data |= mask
        else:
            data &= ~mask
        self._register(register, bytearray((data,)))
    def datetime(self, datetime=None):
        if datetime is None:
            buffer = self.i2c.readfrom_mem(self.address,
                                           self._DATETIME_REGISTER, 7)
            if self._SWAP_DAY_WEEKDAY:
                day = buffer[3]
                weekday = buffer[4]
            else:
                day = buffer[4]
                weekday = buffer[3]
            return datetime_tuple(
                year=_bcd2bin(buffer[6]) + 2000,
                month=_bcd2bin(buffer[5]),
                day=_bcd2bin(day),
                weekday=_bcd2bin(weekday),
                hour=_bcd2bin(buffer[2]),
                minute=_bcd2bin(buffer[1]),
                second=_bcd2bin(buffer[0]),
            )
        datetime = datetime_tuple(*datetime)
        buffer = bytearray(7)
        buffer[0] = _bin2bcd(datetime.second)
        buffer[1] = _bin2bcd(datetime.minute)
        buffer[2] = _bin2bcd(datetime.hour)
        if self._SWAP_DAY_WEEKDAY:
            buffer[4] = _bin2bcd(datetime.weekday)
            buffer[3] = _bin2bcd(datetime.day)
        else:
            buffer[3] = _bin2bcd(datetime.weekday)
            buffer[4] = _bin2bcd(datetime.day)
        buffer[5] = _bin2bcd(datetime.month)
        buffer[6] = _bin2bcd(datetime.year - 2000)
        self._register(self._DATETIME_REGISTER, buffer)
class DS3231(_BaseRTC):
    _CONTROL_REGISTER = 0x0e
    _STATUS_REGISTER = 0x0f
    _DATETIME_REGISTER = 0x00
    _ALARM_REGISTERS = (0x08, 0x0b)
    _SQUARE_WAVE_REGISTER = 0x0e
    _DS3231_1HZ_REGISTER = 0x00
    def lost_power(self):
        return self._flag(self._STATUS_REGISTER, 0b10000000)
    def alarm(self, value=None, alarm=0):
        return self._flag(self._STATUS_REGISTER,
                          0b00000011 & (1 << alarm), value)
    def stop(self, value=None):
        return self._flag(self._CONTROL_REGISTER, 0b10000000, value)
    def sqw_1hz(self, value=None):
        self._register(self._CONTROL_REGISTER, bytearray((self._DS3231_1HZ_REGISTER,)))
        return self._register(self._CONTROL_REGISTER)
    def datetime(self, datetime=None):
        if datetime is not None:
            status = self._register(self._STATUS_REGISTER) & 0b01111111
            self._register(self._STATUS_REGISTER, bytearray((status,)))
        return super().datetime(datetime)