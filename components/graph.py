""" Import the necessary modules for this component to work """
from math import floor
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath, QBrush
from PyQt5.QtWidgets import QLabel, QSizePolicy, QWidget, QVBoxLayout



""" Define the class for the RGraph component """
class RGraph(QLabel):
    def __init__(self, x_points: int = 10, y_points: int = 10, min: int = 0, max: int = 100, hue_offset: int = 0, label: str = ''):
        super().__init__()
        self.setMinimumWidth(100)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setObjectName('RGraph')
        self.x_points = x_points
        self.y_points = y_points
        self.min_val = min
        self.max_val = max
        if self.min_val > self.max_val:
            self.min_val = self.max_val - 1
        self.data = [min] * (x_points + 1)
        self.hue_offset = hue_offset
        self.label = label
        self.pixmap = QPixmap(self.size())
        self.styling = None

    def resizeEvent(self, event):
        self.drawGraph()
        super().resizeEvent(event)

    def drawGraph(self):
        if not self.styling: return
        size = self.size()
        width, height = size.width(), size.height()
        if width <= 0 or height <= 0:
            return
        self.pixmap = QPixmap(width, height)
        self.pixmap.fill(self.styling[0])
        painter = QPainter(self.pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        line_amount_x = floor((width - (width % 40)) / 40)
        line_amount_y = floor((height - (height % 40)) / 40)
        line_distance_x = width / line_amount_x
        line_distance_y = height / line_amount_y
        pen = QPen()
        pen.setWidth(2)
        pen.setColor(self.styling[1])
        painter.setPen(pen)
        for i in range(1, line_amount_x):
            line_x_pos = round(line_distance_x * i)
            painter.drawLine(line_x_pos, 0, line_x_pos, height)
        for i in range(1, line_amount_y):
            line_y_pos = round(line_distance_y * i)
            painter.drawLine(0, line_y_pos, width, line_y_pos)
        pen = QPen()
        pen.setWidth(2)
        pen.setColor(self.styling[2])
        painter.setPen(pen)
        painter.drawRect(0, 0, width, height)
        data_point_distance_x = width / self.x_points
        valRange = self.max_val - self.min_val
        drawable_height = height - 2
        pen.setColor(self.styling[2])
        painter.setPen(pen)
        painter.drawText(5, 15, self.label)
        path = QPainterPath()
        first_x = round(0)
        first_y = round(height - ((self.data[0] - self.min_val) / valRange) * height) + 2
        path.moveTo(first_x, first_y)
        for i, point in enumerate(self.data):
            x_pos = round(data_point_distance_x * i)
            y_pos = round(drawable_height - ((point - self.min_val) / valRange) * drawable_height) + 2
            path.lineTo(x_pos, y_pos)
        path.lineTo(x_pos, height)
        path.lineTo(first_x, height)
        path.closeSubpath()
        fill_color = QColor(self.styling[3])
        fill_color.setAlpha(48)
        painter.setBrush(QBrush(fill_color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        pen = QPen()
        pen.setColor(self.styling[3])
        pen.setWidth(1)
        painter.setPen(pen)
        prev_point = None
        for i, point in enumerate(self.data):
            x_pos = round(data_point_distance_x * i)
            y_pos = round(drawable_height - ((point - self.min_val) / valRange) * drawable_height) + 2
            if prev_point is not None:
                painter.drawLine(prev_point[0], prev_point[1], x_pos, y_pos)
            prev_point = (x_pos, y_pos)
        painter.end()
        self.setPixmap(self.pixmap)

    def updateLatestDatapoint(self, value: float = 0.0):
        append_value = self.min_val if value is None else value
        self.data.pop(0)
        self.data.append(append_value)
        self.drawGraph()

    def get_styling(self):
        palette = self.palette()
        background_color = QColor(palette.color(self.backgroundRole()).name())
        foreground_color = QColor(palette.color(self.foregroundRole()).name())
        bh, bs, bl, _ = background_color.getHsl()
        fh, fs, fl, _ = foreground_color.getHsl()
        fh = (fh + self.hue_offset) % 360
        if bl > 128:
            bl = max(0, bl - 13)
        else:
            bl = min(255, bl + 13)
        bg_secondary = QColor()
        bg_border = QColor()
        bg_secondary.setHsl(bh, bs, bl)
        bg_border.setHsl(bh, bs, 32 if bl > 128 else 224)
        foreground_color.setHsl(fh, fs, fl)
        return [background_color, bg_secondary, bg_border, foreground_color]

    def showEvent(self, event):
        self.styling = self.get_styling()
        self.drawGraph()
        super().showEvent(event)
