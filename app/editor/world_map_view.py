from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QPen

from app.editor.map_view import SimpleMapView
from app.data.overworld import OverworldPrefab

from app.sprites import SPRITES
from app.constants import TILEWIDTH, TILEHEIGHT
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.editor import timer
import app.editor.utilities as editor_utilities
from app.editor.tile_editor import tile_model


class WorldMapView(SimpleMapView):
    def __init__(self):
        super().__init__()
        self.selected = None

    def set_current_level(self, overworld_nid):
        overworld = DB.overworlds.get(overworld_nid)
        if isinstance(overworld, OverworldPrefab):
            self.current_level = overworld
            self.current_map = RESOURCES.tilemaps.get(overworld.tilemap)
            self.update_view()        
    
    def set_selected(self, sel):
        self.selected = sel
        self.update_view()
        
    def update_view(self, _=None):
        if(self.current_level and not self.current_map):
            self.current_map = RESOURCES.tilemaps.get(
                self.current_level.tilemap)
        if self.current_map:
            pixmap = tile_model.create_tilemap_pixmap(self.current_map)
            self.working_image = pixmap
        else:
            self.clear_scene()
            return
        self.paint_roads(self.current_level)
        self.paint_nodes(self.current_level)
        self.paint_selected()
        self.show_map()

    def draw_node(self, painter, node, position, opacity=False):
        icon_nid = node.icon
        num = timer.get_timer().passive_counter.count
        icon = RESOURCES.map_icons.get(icon_nid)
        coord = position
        pixmap = icon.get_pixmap()
        pixmap = QPixmap.fromImage(editor_utilities.convert_colorkey(pixmap.toImage()))
        # to support 16x16, 32x32, and 48x48 map icons, we offset them differently
        offset = (pixmap.height() / 16 - 1) * 8
        if pixmap:
            if opacity:
                painter.setOpacity(0.33)
            painter.drawImage(coord[0] * TILEWIDTH - offset,
                              coord[1] * TILEHEIGHT - offset, pixmap.toImage())
            painter.setOpacity(1.0)
        else:
            pass

    def draw_road_segment(self, painter, start_position, end_position, selected=False):
        start_x = start_position[0] * TILEWIDTH + TILEWIDTH / 2
        start_y = start_position[1] * TILEHEIGHT + TILEHEIGHT / 2
        end_x = end_position[0] * TILEWIDTH + TILEWIDTH / 2
        end_y = end_position[1] * TILEHEIGHT + TILEHEIGHT / 2
        
        # if this is our current working line, draw an accent to let the user know
        if selected:
            pen = QPen(Qt.yellow, 3, style=Qt.SolidLine)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(pen)  
            painter.drawLine(start_x, start_y, end_x, end_y)
            
        # draw the road segment
        pen = QPen(Qt.darkRed, 2, style=Qt.DotLine)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.drawLine(start_x, start_y, end_x, end_y)
        
    def paint_nodes(self, current_level):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            for node in current_level.overworld_nodes:
                if not node.pos:
                    continue
                self.draw_node(painter, node, node.pos)
            painter.end()
            
    def paint_roads(self, current_level):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            for path in current_level.map_paths.values():
                for i in range(len(path) - 1):
                    self.draw_road_segment(painter, path[i], path[i+1])
            painter.end()

    def paint_selected(self):
        """Draws some sort of accent around the selected object (road, node).
           For the road, draws highlights.
           For the node, draws a cursor around it.
        """
        if self.working_image:
            if isinstance(self.selected, list):
                # this is a road
                self.paint_selected_road(self.selected)
            elif isinstance(self.selected, tuple):
                # this is a selected coord of a node
                self.paint_cursor(self.selected)
            else:
                # ??? None type, or something went wrong. Don't draw
                return

    def paint_selected_road(self, path):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            for i in range(len(path) - 1):
                self.draw_road_segment(painter, path[i], path[i+1], True)
            painter.end()

    def paint_cursor(self, coord):
        if self.working_image:
            painter = QPainter()
            painter.begin(self.working_image)
            coord = coord
            cursor_sprite = SPRITES['cursor']
            if cursor_sprite:
                if not cursor_sprite.pixmap:
                    cursor_sprite.pixmap = QPixmap(cursor_sprite.full_path)
                cursor_image = cursor_sprite.pixmap.toImage().copy(0, 64, 32, 32)
                painter.drawImage(
                    coord[0] * TILEWIDTH - 8, coord[1] * TILEHEIGHT - 5, cursor_image)
            painter.end()
    
    def show_map(self):
        if self.working_image:
            self.clear_scene()
            self.scene.addPixmap(self.working_image)
            
    # these two are in the superclass but are useless in this context, override just in case
    def paint_units(self, current_level):
        pass
    def draw_unit(self, painter, unit, position, opacity=False):
        pass