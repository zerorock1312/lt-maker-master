from __future__ import annotations
from app.utilities.utils import clamp

from enum import Enum
import logging
from typing import Callable, Dict, List, Optional, Tuple, Union

from app.constants import WINHEIGHT, WINWIDTH
from app.engine import engine
from app.utilities.typing import Color4
from PIL import Image
from PIL.Image import LANCZOS, new

from pygame import Surface

from .premade_animations.animation_templates import toggle_anim
from .ui_framework_animation import UIAnimation, animated
from .ui_framework_layout import (HAlignment, ListLayoutStyle, UILayoutHandler,
                                  UILayoutType, VAlignment)
from .ui_framework_styling import UIMetric

class ResizeMode(Enum):
    MANUAL = 0
    AUTO = 1

class ComponentProperties():
    def __init__(self):
        # used by the parent to position
        self.h_alignment: HAlignment = HAlignment.LEFT  # Horizontal Alignment of Component
        self.v_alignment: VAlignment = VAlignment.TOP   # Vertical Alignment of Component

        self.grid_occupancy: Tuple[int, int] = (1, 1)    # width/height that the component takes up in a grid
        self.grid_coordinate: Tuple[int, int] = (0, 0)   # which grid coordinate the component occupies
        
        # used by the component to configure itself
        self.bg: Surface = None                         # bg image for the component
        self.bg_color: Color4 = (0, 0, 0, 0)            # (if no bg) - bg fill color for the component
        self.bg_resize_mode: ResizeMode = (             # whether or not the bg will stretch to fit component
            ResizeMode.MANUAL )

        self.layout: UILayoutType = UILayoutType.NONE   # layout type for the component (see ui_framework_layout.py)
        self.list_style: ListLayoutStyle = (            # list layout style for the component, if using UILayoutType.LIST
            ListLayoutStyle.ROW )

        self.resize_mode: ResizeMode = (                # resize mode; AUTO components will dynamically resize themselves,
            ResizeMode.AUTO )                           # whereas MANUAL components will NEVER resize themselves. 
                                                        # Probably always use AUTO, since it'll use special logic.
        
        self.max_width: str = '100%'                      # maximum width str for the component. 
                                                        # Useful for dynamic components such as dialog.
        self.max_height: str = '100%'                     # maximum height str for the component.
        
        self.opacity: float = 1                         # layer opacity for the element.
                                                        # NOTE: changing this from 1 will disable per-pixel alphas
                                                        # for the entire component.


class RootComponent():
    """Dummy component to simulate the top-level window
    """
    def __init__(self):
        self.width: int = WINWIDTH
        self.height: int = WINHEIGHT

class UIComponent():
    def __init__(self, name: str = "", parent: UIComponent = None):
        """A generic UI component. Contains convenient functionality for
        organizing a UI, as well as UI animation support.
        
        NOTE: If using percentages, all of width, height, offset, and margin
        are stored as percentages of the size of the parent, while
        padding is stored as a percentage of the self's size.
        
        Margin and Padding are stored as Left, Right, Top, and Bottom.
        
        self.children are UI component children.
        self.manual_surfaces are manually positioned surfaces, to support more primitive
            and direct control over the UI.
        """
        if not parent:
            self.parent = RootComponent()
        else:
            self.parent = parent
        
        self.layout_handler = UILayoutHandler(self)

        self.name = name
        
        self.children: List[UIComponent] = []
        self.manual_surfaces: List[Tuple[Tuple[int, int], Surface]] = []
        
        self.props: ComponentProperties = ComponentProperties()
        
        self.isize: List[UIMetric] = [UIMetric.percent(100),
                                      UIMetric.percent(100)]
        
        self.imargin: List[UIMetric] = [UIMetric.pixels(0),
                                        UIMetric.pixels(0),
                                        UIMetric.pixels(0),
                                        UIMetric.pixels(0)]
        
        self.ipadding: List[UIMetric] = [UIMetric.pixels(0),
                                         UIMetric.pixels(0),
                                         UIMetric.pixels(0),
                                         UIMetric.pixels(0)]
        
        # temporary offset (horizontal, vertical) - used for animations
        self.ioffset: List[UIMetric] = [UIMetric.pixels(0),
                                        UIMetric.pixels(0)]
    
        # scroll offset
        self.iscroll: List[UIMetric] = [UIMetric.pixels(0),
                                        UIMetric.pixels(0)]
        
        self.cached_background: Surface = None # contains the rendered background.
        
        # animation queue
        self.queued_animations: List[UIAnimation] = []
        # saved animations
        self.saved_animations: Dict[str, List[UIAnimation]] = {}
        # animation speed-up
        self.animation_speed: int = 1
        
        # secret internal timekeeper, basically never touch this
        self._chronometer: Callable[[], int] = engine.get_time
        self._last_update: int = self._chronometer()

        self.enabled: bool = True
        
    def set_chronometer(self, chronometer: Callable[[], int]):
        self._chronometer = chronometer
        self._last_update = self._chronometer()
        for child in self.children:
            child.set_chronometer(chronometer)
    
    @classmethod
    def create_base_component(cls, win_width=WINWIDTH, win_height=WINHEIGHT) -> UIComponent:
        """Creates a blank component that spans the entire screen; a base component
        to which other components can be attached. This component should not be used
        for any real rendering; it is an organizational tool, and should not be
        animated.
        
        Args:
            win_width (int): pixel width of the window. Defaults to the global setting.
            win_height(int): pixel height of the window. Defaults to the global setting.

        Returns:
            UIComponent: a blank base component
        """
        base = cls()
        base.width = win_width
        base.height = win_height
        return base
    
    @classmethod
    def from_existing_surf(cls, surf: Surface) -> UIComponent:
        """Creates a sparse UIComponent from an existing surface.

        Args:
            surf (Surface): Surface around which the UIComponent shall be wrapped

        Returns:
            UIComponent: A simple, unconfigured UIComponent consisting of a single surf
        """
        component = cls()
        component.width = surf.get_width()
        component.height = surf.get_height()
        component.set_background(surf)
        return component
    
    def set_background(self, bg: Union[Surface, Color4]):
        """Set the background of this component to bg_surf.
        If the size doesn't match, it will be rescaled on draw.

        Args:
            bg_surf (Surface): Any surface.
        """
        if isinstance(bg, Surface):
            self.props.bg = bg
        elif isinstance(bg, Color4):
            self.props.bg_color = bg
        # set this to none; the next time we render,
        # the component will regenerate the background.
        # See _create_bg_surf() and to_surf()
        self.cached_background = None
        
    def set_bg_resize(self, mode: ResizeMode):
        """Changes the resizing policy of the bg for this component.

        Args:
            mode (ResizeMode): a resize policy
        """
        self.props.resize_mode = mode
        # set this to none; the next time we render,
        # the component will regenerate the background.
        # See _create_bg_surf() and to_surf()
        self.cached_background = None
    
    @property
    def max_width(self) -> int:
        """Returns max width in pixels

        Returns:
            int: max width of component
        """
        return UIMetric.parse(self.props.max_width).to_pixels(self.parent.width)
    
    @max_width.setter
    def max_width(self, max_width: str):
        """sets max width
        """
        self.props.max_width = max_width
        self._reset('max_width')
    
    @property
    def max_height(self) -> int:
        """return max height in pixels

        Returns:
            int: max height of component
        """
        return UIMetric.parse(self.props.max_height).to_pixels(self.parent.height)
    
    @max_height.setter
    def max_height(self, max_height: str):
        """sets max width
        """
        self.props.max_height = max_height
        self._reset('max_height')
    
    @property
    def offset(self) -> Tuple[int, int]:
        """returns offset in pixels

        Returns:
            Tuple[int, int]: pixel offset value
        """
        return (self.ioffset[0].to_pixels(self.parent.width),
                self.ioffset[1].to_pixels(self.parent.height))

    @offset.setter
    def offset(self, new_offset: Tuple[str, str]):
        """sets offset

        Args:
            new_offset (Tuple[str, str]): offset str,
                can be in percentages or pixels
        """
        self.ioffset = (UIMetric.parse(new_offset[0]), UIMetric.parse(new_offset[1]))
    
    @property
    def scroll(self) -> Tuple[int, int]:
        """returns scroll in pixels

        Returns:
            Tuple[int, int]: scroll offset value
        """
        return (self.iscroll[0].to_pixels(self.width),
                self.iscroll[1].to_pixels(self.height))
    
    @scroll.setter
    def scroll(self, new_scroll: Tuple[str | UIMetric, str | UIMetric]):
        """sets scroll

        Args:
            new_scroll (Tuple[str, str]): offset str,
                can be in percentages or pixels
        """
        if isinstance(new_scroll[0], UIMetric):
            scroll_x = new_scroll[0]
            scroll_y = new_scroll[1]
        else: # parse them
            scroll_x = UIMetric.parse(new_scroll[0])
            scroll_y = UIMetric.parse(new_scroll[1])
        cap_scroll_x = clamp(scroll_x.to_pixels(self.width), 0, self.twidth - self.width)
        cap_scroll_y = clamp(scroll_y.to_pixels(self.height), 0, self.theight - self.height)
        self.iscroll = (UIMetric.parse(cap_scroll_x), UIMetric.parse(cap_scroll_y))
    
    @property
    def size(self) -> Tuple[int, int]:
        """Returns the pixel width and height of the component

        Returns:
            Tuple[int, int]: (pixel width, pixel height)
        """
        return (self.width, self.height)
    
    @property
    def tsize(self) -> Tuple[int, int]:
        """Returns the true pixel width and height of the component

        Returns:
            Tuple[int, int]: (pixel width, pixel height)
        """
        return (self.twidth, self.theight)
    
    @size.setter
    def size(self, size_input: Tuple[str, str]):
        """sets the size of the component

        Args:
            size (Tuple[str, str]): a pair of strings (width, height).
                Can be percentages or flat pixels.
        """
        self.isize = [UIMetric.parse(size_input[0]),
                      UIMetric.parse(size_input[1])]
    
    @property
    def width(self) -> int:
        """display width of component in pixels

        Returns:
            int: pixel width
        """
        if self.props.max_width:
            max_width = UIMetric.parse(self.props.max_width).to_pixels(self.parent.width)
            return min(self.isize[0].to_pixels(self.parent.width), max_width)
        else:
            return self.isize[0].to_pixels(self.parent.width)
        
    @property
    def twidth(self) -> int:
        """true width of component in pixels

        Returns:
            int: pixel width
        """
        return self.isize[0].to_pixels(self.parent.width)
    
    @width.setter
    def width(self, width: str):
        """Sets width

        Args:
            width (str): width string. Can be percentage or pixels.
        """
        self.isize[0] = UIMetric.parse(width)
    
    @property
    def height(self) -> int:
        """display height of component in pixels

        Returns:
            int: pixel height
        """
        if self.props.max_height:
            max_height = UIMetric.parse(self.props.max_height).to_pixels(self.parent.height)
            return min(self.isize[1].to_pixels(self.parent.height), max_height)
        else:
            return self.isize[1].to_pixels(self.parent.height)
        
    @property
    def theight(self) -> int:
        """true height of component in pixels

        Returns:
            int: pixel height
        """
        return self.isize[1].to_pixels(self.parent.height)
    
    @height.setter
    def height(self, height: str):
        """Sets height

        Args:
            height (str): height string. Can be percentage or pixels.
        """
        self.isize[1] = UIMetric.parse(height)
    
    @property
    def margin(self) -> Tuple[int, int, int, int]:
        """margin of component in pixels

        Returns:
            Tuple[int, int, int, int]: pixel margins (left, right, top, bottom)
        """
        return (self.imargin[0].to_pixels(self.parent.width),
                self.imargin[1].to_pixels(self.parent.width),
                self.imargin[2].to_pixels(self.parent.height),
                self.imargin[3].to_pixels(self.parent.height))
        
    @margin.setter
    def margin(self, margin: Tuple[str, str, str, str]):
        """sets a margin

        Args:
            margin (Tuple[str, str, str, str]): margin string.
                Can be in pixels or percentages
        """
        self.imargin = [UIMetric.parse(margin[0]),
                        UIMetric.parse(margin[1]),
                        UIMetric.parse(margin[2]),
                        UIMetric.parse(margin[3])]
    
    @property
    def padding(self) -> Tuple[int, int, int, int]:
        """Padding of component in pixels

        Returns:
            Tuple[int, int, int, int]: pixel padding (left, right, top, bottom)
        """
        return (self.ipadding[0].to_pixels(self.width),
                self.ipadding[1].to_pixels(self.width),
                self.ipadding[2].to_pixels(self.height),
                self.ipadding[3].to_pixels(self.height))

    @padding.setter
    def padding(self, padding: Tuple[str, str, str, str]):
        """sets a padding

        Args:
            padding (Tuple[str, str, str, str]): padding str.
                Can be in pixels or percentages
        """
        self.ipadding = [UIMetric.parse(padding[0]),
                         UIMetric.parse(padding[1]),
                         UIMetric.parse(padding[2]),
                         UIMetric.parse(padding[3])]
        self._reset("padding")
    
    def add_child(self, child: UIComponent):
        """Add a child component to this component.
        NOTE: Order matters, depending on the layout
        set in UIComponent.props.layout.
        
        Also triggers a component reset, if the component is dynamically sized.

        Args:
            child (UIComponent): a child UIComponent
        """
        child.parent = self
        child.set_chronometer(self._chronometer)
        self.children.append(child)
        if self.props.resize_mode == ResizeMode.AUTO:
            self._reset('add_child')
        
    def has_child(self, child_name: str) -> bool:
        for child in self.children:
            if child_name == child.name:
                return True
        return False
    
    def get_child(self, child_name: str) -> Optional[UIComponent]:
        for child in self.children:
            if child_name == child.name:
                return child
        return None
        
    def remove_child(self, child_name: str) -> bool:
        """remove a child from this component.

        Args:
            child_name (str): name of child component.
            
        Returns:
            bool: whether or not the child existed in the first place to be removed
        """
        for idx, child in enumerate(self.children):
            if child.name == child_name:
                self.children.pop(idx)
                return True
        return False
        
    def add_surf(self, surf: Surface, pos: Tuple[int, int]):
        """Add a hard-coded surface to this component.

        Args:
            surf (Surface): A Surface
            pos (Tuple[int, int]): the coordinate position of the top left of surface
        """
        self.manual_surfaces.append((pos, surf))
        
    def speed_up_animation(self, multiplier: int):
        """scales the animation of the component and its children

        Args:
            multiplier (int): the animation speed to be set
        """
        self.animation_speed = multiplier
        for child in self.children:
            child.speed_up_animation(multiplier)
        
    def is_animating(self) -> bool:
        """
        Returns:
            bool: Is this component currently in the middle of an animation
        """
        return len(self.queued_animations) != 0
        
    def any_children_animating(self) -> bool:
        """Returns whether or not any children are currently in the middle of an animation.
        Useful for deciding whether or not to shut this component down.

        Returns:
            bool: Are any children recursively animating?
        """
        for child in self.children:
            if child.any_children_animating():
                return True
            if len(child.queued_animations) > 0:
                return True
        return False

    @animated('!enter')
    def enter(self):
        """the component enters, i.e. allows it to display.

        Because of the @animated tag, will automatically queue
        the animation named "!enter" if it exists in the UIObject's
        saved animations
        """
        for child in self.children:
            child.enter()
        self.enabled = True
    
    @animated('!exit')
    def exit(self, is_top_level=True) -> bool:
        """Makes the component exit, i.e. transitions it out

        Because of the @animated tag, will automatically queue
        the animation named "!exit" if it exists in the UIObject's
        saved animations
        
        This will also recursively exit any children.
        
        Args:
            is_top_level (bool): Whether or not this is the top level parent.
            If not, then this will not actually disable. This is because if
            you disable a top-level component, then you will never render its children
            anyway; this will avoid graphical bugs such as children vanishing instantly
            before the parent animates out.
        
        Returns:
            bool: whether or not this is disabled, or is waiting on children to finish animating.
        """
        for child in self.children:
            child.exit(False)
        if not is_top_level:
            return
        if self.any_children_animating() or self.is_animating():
            # there's an animation playing; wait until afterwards to exit it
            self.queue_animation([toggle_anim(False)], force=True)
        else:
            self.enabled = False

    def enable(self):
        """does the same thing as enter(), except forgoes all animations
        """
        self.enabled = True
        for child in self.children:
            child.enable()

    def disable(self, is_top_level=True):
        """Does the same as exit(), except forgoes all animations.
        """
        self.enabled = False
        
    def queue_animation(self, animations: List[UIAnimation] = [], names: List[str] = [], force: bool = False):
        """Queues a series of animations for the component. This method can be called with
        arbitrary animations to play, or it can be called with names corresponding to
        an animation saved in its animation dict, or both, with names taking precedence. 
        The animations will automatically trigger in the order in which they were queued.

        NOTE: by default, this does not allow queueing when an animation is already playing.

        Args:
            animation (List[UIAnimation], optional): A list of animations to queue. Defaults to [].
            name (List[str], optional): The names of saved animations. Defaults to [].
            force (bool, optional): Whether or not to queue this animation even if other animations are already playing. 
            Defaults to False.
        """
        if not force and self.is_animating():
            return
        for name in names:
            if name in self.saved_animations:
                n_animation = self.saved_animations[name]
                for anim in n_animation:
                    anim.component = self
                    self.queued_animations.append(anim)
        for animation in animations:
            animation.component = self
            self.queued_animations.append(animation)
        
    def push_animation(self, animations: List[UIAnimation] = [], names: List[str] = []):
        """Pushes an animation onto the animation stack, effectively pausing
        the current animation and starting another one. N.B. this will not call
        the "begin_anim" function of the first animation upon it resuming, so using this may result in
        graphical "glitches". Don't use this unless you know exactly why you're using it.

        Args:
            animation (UIAnimation): The UIAnimation to push and begin *right now*.
        """
        for name in names[::-1]:
            if name in self.saved_animations:
                n_animation = self.saved_animations[name]
                for anim in n_animation[::-1]:
                    self.queued_animations.insert(0, anim)
        
        for animation in animations[::-1]:
            animation.component = self
            self.queued_animations.insert(0, animation)
    
    def save_animation(self, animation: UIAnimation, name: str):
        """Adds an animation to the UIComponent's animation dict.
        This is useful for adding animations that may be called many times.

        Args:
            animation (UIAnimation): [description]
            name (str): [description]
        """
        if name in self.saved_animations:
            self.saved_animations[name].append(animation)
        else:
            self.saved_animations[name] = [animation]
        
    def skip_next_animation(self):
        """Finishes the next animation immediately
        """
        current_num_animations = len(self.queued_animations)
        while len(self.queued_animations) >= current_num_animations and len(self.queued_animations) > 0:
            self.update(100)
        
    def skip_all_animations(self):
        """clears the animation queue by finishing all of them instantly, except for unskippable animations
        Useful for skip button implementation.
        """
        for child in self.children:
            child.skip_all_animations()
            
        # remove unskippable animations from queue
        unskippables = [anim for anim in self.queued_animations if not anim.skippable]
        self.queued_animations = list(filter(lambda anim: anim.skippable, self.queued_animations))
        while len(self.queued_animations) > 0:
            self.update(100)
        self.queued_animations = unskippables
        
    def update(self, manual_delta_time=0):
        """update. used at the moment to advance animations.
        """
        if manual_delta_time > 0:
            delta_time = manual_delta_time
        else:
            delta_time = (self._chronometer() - self._last_update) * self.animation_speed
        self._last_update = self._chronometer()
        if len(self.queued_animations) > 0:
            try:
                if self.queued_animations[0].update(delta_time):
                    # the above function call returns True if the animation is finished
                    self.queued_animations.pop(0)
            except Exception as e:
                logging.exception('%s: Animation exception! Aborting animation for component %s. Error message: %s', 
                                  'ui_framework.py:update()', 
                                  self.name,
                                  repr(e))
                self.queued_animations.pop(0)
                
    def _reset(self, reason: str=None):
        """Resets internal state. Triggers on dimension change, so as to allow
        dynamically resized subclasses to resize on prop change.
        
        Args:
            reason (str): the source of the reset call; usually the name of the function or property
            (e.g. 'size')
        """
        pass
    
    def _create_bg_surf(self) -> Surface:
        """Generates the background surf for this component of identical dimension
        as the component itself. If the background image isn't the same size as the component,
        and we want to rescale, then we will use PIL to rescale. Because rescaling is expensive, 
        we'll be making use of limited caching here.

        Returns:
            Surface: A surface of size self.width x self.height, containing a scaled background image.
        """
        if self.props.bg is None:
            surf = engine.create_surface(self.tsize, True)
            surf.fill(self.props.bg_color)
            return surf
        else:
            if not self.cached_background or not self.cached_background.get_size() == self.tsize:
                if self.props.bg_resize_mode == ResizeMode.AUTO:
                    bg_raw = engine.surf_to_raw(self.props.bg, 'RGBA')
                    pil_bg = Image.frombytes('RGBA', self.props.bg.get_size(), bg_raw, 'raw')
                    pil_bg = pil_bg.resize(self.tsize, resample=LANCZOS)
                    bg_scaled = engine.raw_to_surf(pil_bg.tobytes('raw', 'RGBA'), self.tsize, 'RGBA')
                    self.cached_background = bg_scaled
                else:
                    base = engine.create_surface(self.tsize, True)
                    base.blit(self.props.bg, (0, 0))
                    self.cached_background = base
            return self.cached_background

    def to_surf(self) -> Surface:
        if not self.enabled:
            return engine.create_surface(self.size, True)
        # draw the background.
        base_surf = self._create_bg_surf().copy()
        # position and then draw all children recursively according to our layout
        for child in self.children:
            child.update()
        for idx, child_pos in enumerate(self.layout_handler.generate_child_positions()):
            child = self.children[idx]
            base_surf.blit(child.to_surf(), child_pos)
        # draw the hard coded surfaces as well.
        for hard_code_child in self.manual_surfaces:
            pos = hard_code_child[0]
            img = hard_code_child[1]
            base_surf.blit(img, (pos[0], pos[0]))
        
        # scroll the component
        scroll_x, scroll_y = self.scroll
        scroll_width = min(self.twidth - scroll_x, self.width)
        scroll_height = min(self.theight - scroll_y, self.height)
        ret_surf = engine.subsurface(base_surf, (scroll_x, scroll_y, scroll_width, scroll_height))
        
        # handle own opacity
        if self.props.opacity < 1:
            opacity_val = self.props.opacity * 255
            ret_surf.set_alpha(opacity_val)
        return ret_surf
