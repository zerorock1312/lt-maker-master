from __future__ import annotations

from enum import Enum
from typing import Union

from app.utilities import str_utils

class MetricType(Enum):
  PIXEL = 0
  PERCENTAGE = 1

class UIMetric():
  """A wrapper that handles the two types of length measurement, pixels and percentages, 
  and provides functions that handle, convert, and parse strings into these measurements.
  
  Effectively a barebones substitution of the way CSS handles length measurements.
  """
  def __init__(self, val: int, mtype: MetricType):
    self.val = int(val)
    self.mtype = mtype
    
  def is_pixel(self):
    return self.mtype == MetricType.PIXEL
  
  def is_percent(self):
    return self.mtype == MetricType.PERCENTAGE
  
  def to_pixels(self, parent_metric: int = 100):
    if self.is_pixel():
      return self.val
    else:
      return int(self.val * parent_metric / 100)
  
  @classmethod
  def pixels(cls, val):
    return cls(val, MetricType.PIXEL)
  
  @classmethod
  def percent(cls, val):
    return cls(val, MetricType.PERCENTAGE)
  
  @classmethod
  def parse(cls, metric_string):
    """Parses a metric mtype from some arbitrary given input.
    Basically, "50%" becomes a 50% UIMetric, while all other
    formatting: 50, "50px", "50.0", become 50 pixel UIMetric.

    Args:
        metric_string Union[str, int]: string or integer input

    Returns:
        UIMetric: a UIMetric corresponding to the parsed value
    """
    try:
      if isinstance(metric_string, (float, int)):
        return cls(metric_string, MetricType.PIXEL)
      elif isinstance(metric_string, str):
        if str_utils.is_int(metric_string):
          return cls(int(metric_string), MetricType.PIXEL)
        elif str_utils.is_float(metric_string):
          return cls(int(metric_string), MetricType.PIXEL)
        elif 'px' in metric_string:
          metric_string = metric_string[:-2]
          return cls(int(metric_string), MetricType.PIXEL)
        elif '%' in metric_string:
          metric_string = metric_string[:-1]
          return cls(int(metric_string), MetricType.PERCENTAGE)
    except Exception:
      # the input string was incorrectly formatted
      return cls(0, MetricType.PIXEL)

  #################################
  # magic methods for metric math #
  ################################# 
  def __add__(self, other: Union[UIMetric, float, int, str]):
    if isinstance(other, str):
      other = UIMetric.parse(str)
    if isinstance(other, UIMetric):
      if self.mtype == other.mtype:
        return UIMetric(self.val + other.val, self.mtype)
      else:
        raise TypeError('UIMetrics not of same type')
    elif isinstance(other, (float, int)):
      return UIMetric(self.val + other, self.mtype)
    
  def __radd__(self, other):
    return other + self
    
  def __sub__(self, other: Union[UIMetric, float, int, str]):
    if isinstance(other, str):
      other = UIMetric.parse(str)
    if isinstance(other, UIMetric):
      if self.mtype == other.mtype:
        return UIMetric(self.val - other.val, self.mtype)
      else:
        raise TypeError('UIMetrics not of same type')
    elif isinstance(other, (float, int)):
      return UIMetric(self.val - other, self.mtype)
    
  def __rsub__(self, other):
    if isinstance(other, str):
      other = UIMetric.parse(str)
    if isinstance(other, UIMetric):
      if self.mtype == other.mtype:
        return UIMetric(other.val - self.val, self.mtype)
      else:
        raise TypeError('UIMetrics not of same type')
    elif isinstance(other, (float, int)):
      return UIMetric(other - self.val, self.mtype)
    
  def __mul__(self, other: Union[float, int]):
    if isinstance(other, (float, int)):
      return UIMetric(self.val * other, self.mtype)
    
  def __rmul__(self, other: Union[float, int]):
    return self * other
  
  def __truediv__(self, other: Union[float, int]):
    return self * (1 / other)