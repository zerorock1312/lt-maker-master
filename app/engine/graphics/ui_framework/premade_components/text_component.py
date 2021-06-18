from __future__ import annotations
from app.sprites import SPRITES

from typing import List, TYPE_CHECKING, Tuple, Union
import re

from app.engine import engine, text_funcs
from app.engine.bmpfont import BmpFont
from app.engine.fonts import FONT
from app.engine.graphics.ui_framework.ui_framework_styling import UIMetric
from app.utilities.utils import clamp

if TYPE_CHECKING:
    from pygame import Surface

from ..ui_framework import ComponentProperties, ResizeMode, UIComponent


class TextProperties(ComponentProperties):
    """Properties that are particular to text-based components.
    """
    def __init__(self):
        super().__init__()
        self.font: BmpFont = FONT['text-white']         # self-explanatory: the font
        self.line_break_size: str = '0px'               # if the text component is multiline, how much space
                                                        # is between the two lines. Can be percentage or pixel value.
        
        self.max_lines: int = 2                         # maximum number of lines to split the text over, if max_width is set.
                                                        # if 0, then it will

class TextComponent(UIComponent):
    """A component consisting purely of text
    """
    def __init__(self, name: str = "", text: str = "", parent: UIComponent = None):
        super().__init__(name=name, parent=parent)
        self.props: TextProperties = TextProperties()
        self.text = text
        self.num_visible_chars = len(text)
        self._final_formatted_text = []
        self.scrolled_line: float = 1
        self._reset('__init__')
        
    @property
    def wrapped_text(self) -> str:
        if not self._final_formatted_text:
            self._add_line_breaks_to_text()
        return str.join("", self._final_formatted_text)       

    @property
    def font_height(self) -> int:
        return self.props.font.height

    @property
    def max_text_area_width(self) -> int:
        return UIMetric.parse(self.props.max_width).to_pixels(self.parent.width) - self.padding[0] - self.padding[1]
    
    @property
    def max_text_area_height(self) -> int:
        if self.props.max_lines:
            return self.props.max_lines * self.font_height + (self.props.max_lines - 1) * self.line_break_size
        else:
            return self.height
    
    @property
    def line_break_size(self) -> int:
        return UIMetric.parse(self.props.line_break_size).to_pixels(self.parent.height)
        
    @property
    def scrollable_height(self):
        return self.height - self.max_text_area_height
        
    @property
    def lines_displayed(self) -> int:
        """How many lines are we currently displaying?

        Returns:
            int: [description]
        """
        total_displayed_lines = 0
        remaining_chars = self.num_visible_chars - 1
        for line_num, line in enumerate(self._final_formatted_text):
            if remaining_chars <= 0:
                break
            total_displayed_lines = line_num + 1
            remaining_chars -= len(line)
            
        if not self.props.max_lines: # if there's no max line limit, we're displaying all of them
            return total_displayed_lines
        else: # calculate with scroll
            scrolled_lines = max(total_displayed_lines - self.scrolled_line + 1, 0)
            return min(scrolled_lines, self.props.max_lines)
    
    def set_font(self, font: BmpFont):
        """Sets the font of this component and recalculates the component size.

        Args:
            font (BmpFont): font to use to draw the text
        """
        self.props.font = font
        self._reset("font")

    def set_line_break_size(self, line_break_size: str):
        """Sets the line break size of this component and recalculates the component size.

        Args:
            line_break_size (str): pixel or percentage measure for how much space is between
            the lines of text. Percentage measured in size of parent.
        """
        self.props.line_break_size = line_break_size
        self._reset("set_line_break_size")
        
    def set_num_lines(self, num_lines: int):
        """Sets the max lines of this component and recalculates the component size.

        Args:
            num_lines (int): max number of lines
        """
        self.props.max_lines = num_lines
        self._reset("set_num_lines")        

    # @overrides UIComponent._reset
    def _reset(self, _=None):
        """Resets component state
        """
        self.skip_all_animations()
        self.scrolled_line = 1
        self._add_line_breaks_to_text()
        self._recalculate_size()
        
    def _recalculate_size(self):
        """Given our formatted text and our font, we can easily determine
        the size of the text component. This resets all state values,
        since things like scroll may no longer apply.
        """
        # calculate size
        if self.props.resize_mode == ResizeMode.AUTO:
            num_lines = len(self._final_formatted_text)
            if num_lines == 1:
                # all text is on one line anyway, just go by text
                text_size = self.props.font.size(self.text)
            else:
                # if not, we can just do math with max width
                # and the number of lines plus number of breaks
                height = num_lines * self.font_height + (num_lines - 1) * self.line_break_size
                text_size = self.max_text_area_width, height
            self.size = (text_size[0] + 2 + self.padding[0] + self.padding[1],
                         text_size[1] + self.padding[2] + self.padding[3])

    def set_text(self, text: str):
        """Sets the text of this text component and recalculates the component size.

        Args:
            text (str): Text to display
        """
        self.text = text
        self.num_visible_chars = len(text)
        self._reset('text')
        
    def set_visible(self, num_chars_visible: int):
        """If you do not wish to display all the text at once,
        you can specify how many characters you want to display
        at any given time. Useful for dialog.

        Args:
            num_visible_chars (int): number of chars, starting from the beginning
            of the text, to display
        """
        self.num_visible_chars = num_chars_visible

    # @overrides UIComponent._create_bg_surf()
    def _create_bg_surf(self) -> Surface:
        """Generates an appropriately-sized text transparent background
        according to our size.

        Returns:
            Surface: a correctly-sized transparent surf.
        """
        # if we don't have cached, or our size has changed since last background generation, regenerate
        if not self.cached_background or self.cached_background.get_size() != self.tsize:
            self.cached_background = engine.create_surface(self.tsize, True)
        return self.cached_background

    def _add_line_breaks_to_text(self):
        """Generates correctly line-broken text based on 
        our max width. This is stored in the internal list `_final_formatted_text`
        """
        # determine the max length of the string we can fit on the first line
        # we will only split on spaces so as to preserve words on the same line
        if self.props.max_width:
            lines = text_funcs.line_wrap(self.props.font, self.text, self.max_text_area_width)
            self._final_formatted_text = lines
        else:
            self._final_formatted_text = [self.text]
    
    def _pixel_height_to_line(self, pixels):
        return clamp(pixels / self.scrollable_height * len(self._final_formatted_text) + 1, 1, len(self._final_formatted_text))
        
    def scroll_to_nearest_line(self):
        self.scrolled_line = round(self.scrolled_line)

    def set_scroll_height(self, scroll_to: Union[int, float, str, UIMetric]):
        """crops the text component to the place you want to scroll to. This supports
        calculating the y-coord of a specific line or space between two lines (int, float), 
        or a specific pixel or percentage (str, UIMetric)

        Args:
            scroll_to (Union[int, float, str, UIMetric]): location of scroll.
        """
        if isinstance(scroll_to, (int, float)):
            scroll_to = clamp(scroll_to, 1, len(self._final_formatted_text))
            self.scrolled_line = scroll_to
        elif isinstance(scroll_to, str):
            self.scrolled_line = self._pixel_height_to_line(UIMetric.parse(scroll_to).to_pixels(self.scrollable_height))
        elif isinstance(scroll_to, UIMetric):
            self.scrolled_line =  self._pixel_height_to_line(scroll_to.to_pixels(self.scrollable_height))
        else:
            self.scrolled_line = 1
            
    def is_index_at_end_of_line(self, idx: int) -> bool:
        """Is the index at the end of a line?
        Useful for determining if `self.num_visible_chars` has reached a stopping point

        Args:
            idx (int): index of a 'cursor', or how many characters you've theoretically already written

        Returns:
            bool: whether or not the cursor has written to the end of a line
        """
        for line in self._final_formatted_text:
            idx -= len(line)
            if idx == 0:
                return True
            if idx < 0:
                return False
        return False
    
    def is_index_at_sequence(self, idx: int, seq: str) -> bool:
        """Is the index at a specific substring?
        Useful for determining if `self.num_visible_chars` has reached a specific word or,
        in most cases, if it's reached a {w} pause.

        Args:
            idx (int): index of a 'cursor', or how many characters you've theoretically already written
            seq (int): sequence in question

        Returns:
            bool: whether or not the cursor has written to the specified subsequence
        """
        try:
            if self.wrapped_text[idx:].startswith(seq):
                return True
        except:
            pass
        return False
    
    # @overrides UIComponent.to_surf
    def to_surf(self) -> Surface:
        if not self.enabled:
            return engine.create_surface(self.tsize, True)
        # draw the background.
        base_surf = self._create_bg_surf().copy()
        # draw the text
        remaining_chars = self.num_visible_chars
        for line_num, line in enumerate(self._final_formatted_text):
            if remaining_chars <= 0:
                break
            visible_line = line[:remaining_chars]
            remaining_chars -= len(visible_line)
            self.props.font.blit(visible_line, base_surf, pos=(self.padding[0], self.padding[2] + line_num * (self.line_break_size + self.font_height)))
        
        if self.props.max_lines > 0:
            # crop the text to the max number of lines, to avoid overflow
            scrolled_down_height = (self.scrolled_line - 1) * (self.font_height + self.line_break_size)
            ret_surf = engine.subsurface(base_surf, (0, 
                                                     scrolled_down_height, 
                                                     self.width, 
                                                     min(self.max_text_area_height, self.height - scrolled_down_height)))
        else:
            ret_surf = base_surf
        return ret_surf

class DialogTextComponent(TextComponent):
    def __init__(self, name: str="", text: str="", parent: UIComponent=None):
        super().__init__(name=name, text=text, parent=parent)
        self.cursor = SPRITES.get('waiting_cursor')
        self.cursor_y_offset = [0]*20 + [1]*2 + [2]*8 + [1]*2
        self.cursor_y_offset_index = 0
        
    def wiggle_cursor_height(self):
        self.cursor_y_offset_index = (self.cursor_y_offset_index + 1) % len(self.cursor_y_offset)
        return self.cursor_y_offset[self.cursor_y_offset_index] + self.font_height / 3
        
    # @overrides TextComponent.to_surf
    def to_surf(self) -> Surface:
        if not self.enabled:
            return engine.create_surface(self.tsize, True)
        # draw the background.
        base_surf = self._create_bg_surf().copy()
        # draw the text
        remaining_chars = self.num_visible_chars
        for line_num, line in enumerate(self._final_formatted_text):
            if remaining_chars <= 0:
                break
            visible_line = line[:remaining_chars]
            # strip all special commands - {w}, {br}, etc. - from line
            processed_line = re.sub('{[^}]*}?', '', visible_line)
            remaining_chars -= len(visible_line)
            self.props.font.blit(processed_line, base_surf, pos=(self.padding[0], self.padding[2] + line_num * (self.line_break_size + self.font_height)))
            # if we're at a wait point, and this is the last line, blit the waiting cursor sprite
            if remaining_chars <= 0 and self.is_index_at_sequence(self.num_visible_chars, '{w}'):
                cursor_pos = (self.padding[0] + self.props.font.width(processed_line) + self.props.font.width(' '),
                              self.padding[2] + line_num * (self.line_break_size + self.font_height) + self.wiggle_cursor_height())
                base_surf.blit(self.cursor, cursor_pos)
                pass
        
        if self.props.max_lines > 0:
            # crop the text to the max number of lines, to avoid overflow
            scrolled_down_height = (self.scrolled_line - 1) * (self.font_height + self.line_break_size)
            remaining_lines = min(self.props.max_lines, len(self._final_formatted_text) - self.scrolled_line + 1)
            height_of_max_lines = remaining_lines * self.font_height + (remaining_lines - 1) * self.line_break_size
            ret_surf = engine.subsurface(base_surf, (0, scrolled_down_height, self.width, height_of_max_lines))
        else:
            ret_surf = base_surf
        return ret_surf