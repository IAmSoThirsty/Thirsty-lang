"""
Thirsty-Lang Standard Library: DateTime
Comprehensive time and date handling with timezone support

Provides:
- DateTime: Timezone-aware datetime objects
- TimeDelta: Duration arithmetic
- Timezone: UTC and offset-based timezones
- Formatting: ISO 8601 and custom format support
"""

import time
from datetime import datetime as py_datetime, timedelta as py_timedelta, timezone as py_timezone


class DateTime:
    """Timezone-aware datetime object"""
    
    def __init__(self, year, month, day, hour=0, minute=0, second=0, microsecond=0, tzinfo=None):
        self._dt = py_datetime(year, month, day, hour, minute, second, microsecond, tzinfo)
    
    @classmethod
    def now(cls, tz=None):
        """Current datetime in given timezone (UTC if None)"""
        dt = py_datetime.now(tz or py_timezone.utc)
        return cls.from_py_datetime(dt)
    
    @classmethod
    def utcnow(cls):
        """Current UTC datetime"""
        return cls.now(py_timezone.utc)
    
    @classmethod
    def from_timestamp(cls, timestamp, tz=None):
        """Create from Unix timestamp"""
        dt = py_datetime.fromtimestamp(timestamp, tz or py_timezone.utc)
        return cls.from_py_datetime(dt)
    
    @classmethod
    def from_iso(cls, iso_string):
        """Parse ISO 8601 formatted string"""
        dt = py_datetime.fromisoformat(iso_string)
        return cls.from_py_datetime(dt)
    
    @classmethod
    def from_py_datetime(cls, dt):
        """Create from Python datetime"""
        instance = cls.__new__(cls)
        instance._dt = dt
        return instance
    
    def to_iso(self):
        """Format as ISO 8601 string"""
        return self._dt.isoformat()
    
    def timestamp(self):
        """Return Unix timestamp"""
        return self._dt.timestamp()
    
    def replace(self, year=None, month=None, day=None, hour=None, minute=None, second=None, tzinfo=None):
        """Return new DateTime with specified fields replaced"""
        return DateTime.from_py_datetime(self._dt.replace(
            year=year or self._dt.year,
            month=month or self._dt.month,
            day=day or self._dt.day,
            hour=hour or self._dt.hour,
            minute=minute or self._dt.minute,
            second=second or self._dt.second,
            tzinfo=tzinfo if tzinfo is not None else self._dt.tzinfo
        ))
    
    def astimezone(self, tz):
        """Convert to given timezone"""
        return DateTime.from_py_datetime(self._dt.astimezone(tz))
    
    def add(self, delta):
        """Add TimeDelta"""
        return DateTime.from_py_datetime(self._dt + delta._td)
    
    def subtract(self, other):
        """Subtract DateTime or TimeDelta"""
        if isinstance(other, DateTime):
            return TimeDelta.from_py_timedelta(self._dt - other._dt)
        elif isinstance(other, TimeDelta):
            return DateTime.from_py_datetime(self._dt - other._td)
        raise TypeError("Can only subtract DateTime or TimeDelta")
    
    @property
    def year(self):
        return self._dt.year
    
    @property
    def month(self):
        return self._dt.month
    
    @property
    def day(self):
        return self._dt.day
    
    @property
    def hour(self):
        return self._dt.hour
    
    @property
    def minute(self):
        return self._dt.minute
    
    @property
    def second(self):
        return self._dt.second
    
    @property
    def microsecond(self):
        return self._dt.microsecond
    
    def __repr__(self):
        return f"DateTime({self._dt.isoformat()})"
    
    def __str__(self):
        return self._dt.isoformat()


class TimeDelta:
    """Duration for datetime arithmetic"""
    
    def __init__(self, days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0):
        self._td = py_timedelta(
            days=days,
            seconds=seconds,
            microseconds=microseconds,
            milliseconds=milliseconds,
            minutes=minutes,
            hours=hours,
            weeks=weeks
        )
    
    @classmethod
    def from_py_timedelta(cls, td):
        """Create from Python timedelta"""
        instance = cls.__new__(cls)
        instance._td = td
        return instance
    
    @property
    def days(self):
        return self._td.days
    
    @property
    def seconds(self):
        return self._td.seconds
    
    @property
    def microseconds(self):
        return self._td.microseconds
    
    def total_seconds(self):
        """Total duration in seconds"""
        return self._td.total_seconds()
    
    def __repr__(self):
        return f"TimeDelta(days={self.days}, seconds={self.seconds}, microseconds={self.microseconds})"


class Timezone:
    """Timezone utilities"""
    
    @staticmethod
    def utc():
        """UTC timezone"""
        return py_timezone.utc
    
    @staticmethod
    def offset(hours=0, minutes=0):
        """Timezone with offset from UTC"""
        delta = py_timedelta(hours=hours, minutes=minutes)
        return py_timezone(delta)


# Export all datetime classes
__all__ = ['DateTime', 'TimeDelta', 'Timezone']
