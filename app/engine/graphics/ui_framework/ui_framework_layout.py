from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, List, Tuple, Union

if TYPE_CHECKING:
    from .ui_framework import UIComponent

from enum import Enum


class HAlignment(Enum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2
    NONE = 3
    
class VAlignment(Enum):
    TOP = 3
    CENTER = 4
    BOTTOM = 5
    NONE = 6

class UILayoutType(Enum):
    """Enum for distinguishing the types of layouts for a component.
    The layout types are as follows:

        - NONE: Simplest layout. Draws all children naively, i.e. according to their alignment and margins.
                This WILL draw children on top of one another if they occupy the same space.
                This layout is best used for very simple UIs that you exert direct control over,
                such as the game UI that includes unit info and terrain info (whose alignment we control).

        - LIST: Will draw children in order, and align them accordingly in a list. Uses ComponentProperties.list_style to 
                determine whether to draw children top to bottom, left to right, or vice versa. Make sure you proportion
                the children correctly, otherwise they will be cut off or drawn off screen.

        - GRID: The 2D version of the above. Uses ComponentProperties.grid_dimensions to determine the (rows, columns) of the grid.
                Will draw children in order. If you want children to take up more than one slot, use the child's 
                ComponentProperties.grid_occupancy property to determine how many (row_space, column_space) it takes up.
                As with the list, ensure that you proportion the children correctly.

        - MANUAL_GRID: If you wanted more fine control of what goes where, the manual grid will not automatically draw children in order;
                rather, it will draw them according to the child's ComponentProperties.grid_coordinates property. This means that 
                if you do not set the ComponentProperties.grid_coordinates property for some child, it will NOT DRAW PROPERLY (i.e.
                overwrite the first square and muck things up)
    """
    NONE = 0
    LIST = 1
    GRID = 2
    MANUAL_GRID = 3

class ListLayoutStyle(Enum):
    ROW = 0
    COLUMN = 1
    ROW_REVERSE = 2 # right to left
    COLUMN_REVERSE = 3 # bottom to top

class UILayoutHandler():
    """The Layout Handler contains most of the code for handling the different
    UILayoutTypes: NONE, LIST, GRID, and MANUAL_GRID.

    This is mostly organizational, reducing the amount of case handling that I 
    would otherwise need to write in ui_framework.py.
    """
    def __init__(self, parent_component: UIComponent):
        self.parent_component: UIComponent = parent_component

    def generate_child_positions(self) -> List[Tuple[int, int]]:
        """Generates a list positions, order corresponding to the list of children provided.
    
        Returns:
            List[Tuple[int, int]]: List of child positions.
        """
        layout = self.parent_component.props.layout
        if layout == UILayoutType.LIST:
            return self._list_layout()
        elif layout == UILayoutType.GRID:
            pass
        elif layout == UILayoutType.MANUAL_GRID:
            pass
        else: # assume UILayoutType.NONE
            return self._naive_layout()

    def _naive_layout(self) -> List[Tuple[int, int]]:
        """Layout Strategy for the naive UILayoutType.NONE layout.

        Returns:
            List[Tuple[int, int]]: positions of children
        """
        positions = []
        width = self.parent_component.width
        height = self.parent_component.height
        padding = self.parent_component.padding
        for child in self.parent_component.children:
            cwidth, cheight = child.width, child.height
            props = child.props
            top = 0
            left = 0
            # handle horizontal and vertical alignments
            if props.h_alignment is HAlignment.LEFT:
                left = child.margin[0] + padding[0]
            elif props.h_alignment is HAlignment.CENTER:
                left = width / 2 - cwidth / 2
            elif props.h_alignment is HAlignment.RIGHT:
                left = width - (child.margin[1] + cwidth + padding[1])
                
            if props.v_alignment is VAlignment.TOP:
                top = child.margin[2] + padding[2]
            elif props.v_alignment is VAlignment.CENTER:
                top = height / 2 - cheight / 2
            elif props.v_alignment is VAlignment.BOTTOM:
                top = height - (child.margin[3] + cheight + padding[3])
            
            offset = child.offset
            positions.append((left + offset[0], top + offset[1]))
        return positions

    def _list_layout(self) -> List[Tuple[int, int]]:
        """Layout strategy for the UILayoutType.LIST layout.

        Returns:
            List[Tuple[int, int]]: positions of children
        """
        positions = []
        width = self.parent_component.width
        height = self.parent_component.height
        padding = self.parent_component.padding
        ordered_children = self.parent_component.children[:]

        # we build in the padding
        incrementing_position = [self.parent_component.padding[0], self.parent_component.padding[2]]

        # handle different types of lists
        if self.parent_component.props.list_style == ListLayoutStyle.ROW:
            # we increment the x-coordinate
            incrementing_index = 0
        elif self.parent_component.props.list_style == ListLayoutStyle.COLUMN:
            # we increment the y-coordinate
            incrementing_index = 1
        elif self.parent_component.props.list_style == ListLayoutStyle.ROW_REVERSE:
            # we reverse the list so we calculate the last child first (thus simulating a "right to left" list)
            # we increment the x-coordinate
            incrementing_index = 0
            ordered_children = ordered_children[::-1]
        elif self.parent_component.props.list_style == ListLayoutStyle.COLUMN_REVERSE:
            # we reverse the list so we calculate the last child first (thus simulating a "bottom-to-top" list)
            # we increment the y-coordinate
            incrementing_index = 1
            ordered_children = ordered_children[::-1]

        for child in ordered_children:
            csize = (child.width, child.height)
            cmargin_sum = (child.margin[0] + child.margin[1], child.margin[2] + child.margin[3])
            props = child.props

            position = incrementing_position[:]

            # position the child on the off-axis via their alignment:
            if incrementing_index == 0:
                # row list, so align the children as they wish vertically
                if props.v_alignment is VAlignment.TOP:
                    position[1] = child.margin[2] + padding[2]
                elif props.v_alignment is VAlignment.CENTER:
                    position[1] = height / 2 - csize[1] / 2
                elif props.v_alignment is VAlignment.BOTTOM:
                    position[1] = height - (child.margin[3] + csize[1] + padding[3])
            else:
                # column list, align the children as they wish horizontally
                if props.h_alignment is HAlignment.LEFT:
                    position[0] = child.margin[0] + padding[0]
                elif props.h_alignment is HAlignment.CENTER:
                    position[0] = width / 2 - csize[0] / 2
                elif props.h_alignment is HAlignment.RIGHT:
                    position[0] = width - (child.margin[1] + csize[0] + padding[1])
            
            # add the correct, aligned position
            positions.append(position)
            # increment the position by the child's relevant properties for the next child
            incrementing_position[incrementing_index] = (incrementing_position[incrementing_index] + 
                                                         csize[incrementing_index] +
                                                         cmargin_sum[incrementing_index])

        if (self.parent_component.props.list_style == ListLayoutStyle.ROW_REVERSE 
            or self.parent_component.props.list_style == ListLayoutStyle.COLUMN_REVERSE):
            # reverse the positions list so the ordering is accurate
            positions = positions[::-1]
        return positions
