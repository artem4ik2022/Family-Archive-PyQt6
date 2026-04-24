import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem, QPushButton, QVBoxLayout,
                             QHBoxLayout, QWidget, QDialog, QFormLayout, QLineEdit, QTextEdit, QDateEdit, QLabel, QGraphicsPathItem)
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPainterPathStroker

class PersonData:
    def __init__(self, first_name='', last_name='', patronymic="", birth_date=None, death_date=None, bio=""):
        self.first_name = first_name
        self.last_name = last_name
        self.patronymic = patronymic
        self.birth_date = birth_date
        self.death_date = death_date
        self.bio = bio


class PersonDialog(QDialog):
    def __init__(self, parent = None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Человек")
        self.setMinimumWidth(300)
        self.data = data or PersonData()

        layout = QFormLayout(self)

        self.last_name_input = QLineEdit(self.data.last_name)
        self.first_name_input = QLineEdit(self.data.first_name)
        self.patronymic_input = QLineEdit(self.data.patronymic)
        self.bio_input = QTextEdit(self.data.bio)

        layout.addRow("Фамилия:", self.last_name_input)
        layout.addRow("Имя:", self.first_name_input)
        layout.addRow("Отчество:", self.patronymic_input)
        layout.addRow("Биография:", self.bio_input)

        self.photo_btn = QPushButton("Выбрать фото (в разработке)")
        layout.addRow("Фотография:", self.photo_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_and_close)
        layout.addRow(save_btn)
    
    def save_and_close(self):
        self.data.last_name = self.last_name_input.text()
        self.data.first_name = self.first_name_input.text()
        self.data.patronymic = self.patronymic_input.text()
        self.data.bio = self.bio_input.toPlainText()
        self.accept()

class LinkItem:
    def update_position(self):
        pass

class EdgeItem(QGraphicsLineItem, LinkItem):
    def __init__(self, source_node, dest_node):
        super().__init__()
        self.source_node = source_node
        self.dest_node = dest_node
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.setZValue(-1)
        self.update_position()

        def update_position(self):
            p1 = self.source_node.sceneBoundingRect().center()
            p2 = self.dest_node.sceneBoundingRect().center()
            self.setLine(p1.x(), p1.y(), p2.x(), p2.y())


class PersonNode(QGraphicsRectItem):
    def __init__(self, data: PersonData, level=0):
        super().__init__(-60, -30, 120, 60)
        self.data = data
        self.level = level
        self.links = []
        self.is_manual = False
        
        self.setBrush(QBrush(QColor("lightblue")))
        self.setPen(QPen(Qt.GlobalColor.darkBlue, 2))
        self.setFlags(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable | 
                      QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
                      QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setZValue(1)

        self.text_item = QGraphicsTextItem(self)
        self.update_text()

    def update_text(self):
        name = f"{self.data.first_name}\n{self.data.last_name}"
        self.text_item.setPlainText(name if name.strip() else "Неизвестный")
        br = self.text_item.boundingRect()
        self.text_item.setPos(-br.width() / 2, -br.height() / 2)

    def add_edge(self, edge):
        self.links.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.links:
                edge.update_position()
        return super().itemChange(change, value)
    
    def mousePressEvent(self, event):
        self._start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        dialog = PersonDialog(data=self.data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data = dialog.data
            self.update_text()
        super().mouseDoubleClickEvent(event)
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # Если позиция изменилась, фиксируем её и привязываем к "сетке" уровней
        if self.pos() != self._start_pos:
            self.is_manual = True
            grid_y = round(self.y() / 150) * 150
            self.setPos(self.x(), grid_y)
            self.level = int(grid_y / 150)
            # Принудительно обновляем линии
            for edge in self.links:
                edge.update_position()


class TreeGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(self.renderHints())
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)


class MarriageItem(QGraphicsPathItem, LinkItem):
    def __init__(self, node1, node2):
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.child_edges = []
        
        self.setFlags(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        pen = QPen(QColor("gray"), 3, Qt.PenStyle.DashLine)
        self.setPen(pen)
        self.setZValue(-1)
        self.update_position()

    def update_position(self):
        p1 = self.node1.sceneBoundingRect().center()
        p2 = self.node2.sceneBoundingRect().center()
        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        self.setPath(path)
        
        # Обновляем детей, привязанных к этому браку
        for edge in self.child_edges:
            edge.update_position()
    
    def shape(self):
        # Делаем область клика шире, чтобы легче было попасть мышкой
        stroker = QPainterPathStroker()
        stroker.setWidth(20) 
        return stroker.createStroke(self.path())

    def get_center(self):
        return self.path().pointAtPercent(0.5)


class ChildEdge(QGraphicsPathItem, LinkItem):
    def __init__(self, source, child_node):
        """source может быть PersonNode или MarriageItem"""
        super().__init__()
        self.source = source
        self.child_node = child_node
        self.setZValue(-1)
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.update_position()

    def update_position(self):
        # Начальная точка (центр родителя или центр линии брака)
        if isinstance(self.source, MarriageItem):
            start_pos = self.source.get_center()
        else:
            start_pos = self.source.sceneBoundingRect().center()
            
        end_pos = self.child_node.sceneBoundingRect().center()
        
        # Рисуем ломаную линию (вниз -> вбок -> вниз)
        path = QPainterPath()
        path.moveTo(start_pos)
        
        mid_y = start_pos.y() + (end_pos.y() - start_pos.y()) / 2
        path.lineTo(start_pos.x(), mid_y)
        path.lineTo(end_pos.x(), mid_y)
        path.lineTo(end_pos)
        
        self.setPath(path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Семейный архив")
        self.resize(1000, 700)

        self.scene = QGraphicsScene()
        self.view = TreeGraphicsView(self.scene)

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        
        self.main_layout = QVBoxLayout(self.centralWidget)

        self.start_btn = QPushButton("Создать первого человека", self)
        self.start_btn.setFixedSize(250, 50)
        self.start_btn.clicked.connect(self.create_root_person)
        
        self.action_panel = QWidget()
        action_layout = QHBoxLayout(self.action_panel)

        self.add_free_person_btn = QPushButton("Создать человека")

        self.add_parent_btn = QPushButton("Добавить родителя")
        self.add_child_btn = QPushButton("Добавить ребенка")
        self.link_parent_child_btn = QPushButton("Связать (Родитель-Ребенок)")
        self.link_spouses_btn = QPushButton("Связь (Супруги)")
        
        self.add_parent_btn.clicked.connect(lambda: self.add_relative(is_parent=True))
        self.add_child_btn.clicked.connect(lambda: self.add_relative(is_parent=False))
        self.link_parent_child_btn.clicked.connect(self.link_selected_items)
        self.link_spouses_btn.clicked.connect(self.link_selected_nodes)
        self.add_free_person_btn.clicked.connect(self.create_free_person)

        action_layout.addWidget(self.add_free_person_btn)
        action_layout.addWidget(self.add_parent_btn)
        action_layout.addWidget(self.add_child_btn)
        action_layout.addWidget(self.link_parent_child_btn)
        action_layout.addWidget(self.link_spouses_btn)
        self.action_panel.setVisible(False)

        self.main_layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.view)
        self.main_layout.addWidget(self.action_panel)
        self.view.setVisible(False)

        self.scene.selectionChanged.connect(self.on_selection_changed)

    def create_root_person(self):
        dialog = PersonDialog()
        if dialog.exec():
            self.start_btn.setVisible(False)
            self.view.setVisible(True)

            node = PersonNode(dialog.data, level=0)
            self.scene.addItem(node)
            self.rearrange()
            node.setPos(0, 0)
    
    def create_free_person(self):
        dlg = PersonDialog()
        if dlg.exec():
            center = self.view.mapToScene(self.view.viewport().rect().center())

            grid_y = round(center.y() / 150) * 150
            node = PersonNode(dlg.data, level=int(grid_y / 150))
            node.is_manual = True
            self.scene.addItem(node)
            node.setPos(center.x(), grid_y)
            self.rearrange()

    
    def rearrange(self):
        gen = {}
        for i in self.scene.items():
            if isinstance(i, PersonNode): 
                if not i.is_manual:
                    gen.setdefault(i.level, []).append(i)
        for lvl, nodes in gen.items():
            total = len(nodes) * 160 - 40
            x = -total / 2 + 60
            for n in nodes:
                n.setPos(x, lvl * 150)
                x += 160
        for i in self.scene.items():
            if hasattr(i, 'update_position'): i.update_position()
    
    def on_selection_changed(self):
        selected = self.scene.selectedItems()
        person_nodes = [item for item in selected if isinstance(item, PersonNode)]
        marriage_items = [item for item in selected if isinstance(item, MarriageItem)]
        
        # Скрываем всё и показываем по условиям
        self.add_free_person_btn.setVisible(True)
        self.add_parent_btn.setVisible(False)
        self.add_child_btn.setVisible(False)
        self.link_parent_child_btn.setVisible(False)
        self.link_spouses_btn.setVisible(False)
        
        if len(person_nodes) == 1 and not marriage_items:
            self.action_panel.setVisible(True)
            self.add_parent_btn.setVisible(True)
            self.add_child_btn.setVisible(True)
        elif len(person_nodes) == 2:
            self.action_panel.setVisible(True)
            self.link_parent_child_btn.setVisible(True) # Связать двух людей как род-реб
            self.link_spouses_btn.setVisible(True)
        elif len(marriage_items) == 1 and not person_nodes:
            self.action_panel.setVisible(True)
            self.add_child_btn.setVisible(True) # Добавить ребенка К БРАКУ
        elif len(person_nodes) == 1 and len(marriage_items) == 1:
            self.action_panel.setVisible(True)
            self.link_parent_child_btn.setVisible(True) # Привязать существующего человека к браку
        else:
            self.action_panel.setVisible(False)
    
    def link_selected_nodes(self):
        selected = self.scene.selectedItems()
        person_nodes = [item for item in selected if isinstance(item, PersonNode)]
        if len(person_nodes) == 2:
            node1, node2 = person_nodes[0], person_nodes[1]
            marriage = MarriageItem(node1, node2)
            self.scene.addItem(marriage)
            node1.links.append(marriage)
            node2.links.append(marriage)

            for parent in [node1, node2]:
                # Проходим по копии списка связей родителя
                for link in parent.links[:]:
                    # Если это связь с ребенком и этот родитель является источником (source)
                    if isinstance(link, ChildEdge) and link.source == parent:
                        # Переключаем источник на линию брака
                        link.source = marriage
                        marriage.child_edges.append(link)
                        # Удаляем связь из личного списка родителя, так как теперь она в браке
                        parent.links.remove(link)

            self.scene.clearSelection()
            self.rearrange()
    
    def link_selected_items(self):
        # Универсальная связь родитель-ребенок (существующий человек к человеку или браку)
        selected = self.scene.selectedItems()
        person_nodes = [item for item in selected if isinstance(item, PersonNode)]
        marriage_items = [item for item in selected if isinstance(item, MarriageItem)]

        if len(person_nodes) == 2:
            # Один родитель, один ребенок (условно первый выбранный - родитель)
            p1, p2 = person_nodes[0], person_nodes[1]
            edge = ChildEdge(p1, p2)
            self.scene.addItem(edge)
            p1.links.append(edge)
            p2.links.append(edge)
        elif len(person_nodes) == 1 and len(marriage_items) == 1:
            # Привязываем человека как ребенка к линии брака
            child = person_nodes[0]
            marriage = marriage_items[0]
            edge = ChildEdge(marriage, child)
            self.scene.addItem(edge)
            child.links.append(edge)
            marriage.child_edges.append(edge)
        
        self.scene.clearSelection()
        self.rearrange()

    def add_relative(self, is_parent):
        sel = self.scene.selectedItems()[0]
        d = PersonDialog()
        if d.exec():
            lvl = (sel.level - 1 if is_parent else sel.level + 1) if isinstance(sel, PersonNode) else sel.node1.level + 1
            new_node = PersonNode(d.data, lvl)
            self.scene.addItem(new_node)
            edge = ChildEdge(sel, new_node) if not is_parent else ChildEdge(new_node, sel)
            self.scene.addItem(edge)
            new_node.links.append(edge)
            if isinstance(sel, MarriageItem): sel.child_edges.append(edge)
            else: sel.links.append(edge)
            self.scene.clearSelection()
            self.rearrange()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())