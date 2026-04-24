import sys
import zipfile
import json
import uuid
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem, QPushButton, QVBoxLayout,
                             QHBoxLayout, QWidget, QDialog, QFormLayout, QLineEdit, QTextEdit, QDateEdit, QLabel, QGraphicsPathItem, 
                             QWidgetAction, QMenuBar, QMenu, QMessageBox, QFileDialog, QDateTimeEdit)
from PyQt6.QtCore import Qt, QRectF, QPointF, QDate
from PyQt6.QtGui import QPen, QBrush, QColor, QFont, QPainterPath, QPainterPathStroker, QAction

class PersonData:
    def __init__(self, first_name='', last_name='', patronymic="", birth_date=None, death_date=None, bio="", photo_path=None):
        self.first_name = first_name
        self.last_name = last_name
        self.patronymic = patronymic
        self.birth_date = birth_date
        self.death_date = death_date
        self.bio = bio
        self.photo_path = photo_path


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
    def __init__(self, data: PersonData, level=0, node_id=None):
        super().__init__(-60, -30, 120, 60)
        self.id = node_id if node_id else str(uuid.uuid4())
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
            
            if self.scene():
                self.scene().views()[0].window().rearrange()


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
    def __init__(self, node1, node2, node_id=None):
        super().__init__()
        self.id = node_id if node_id else str(uuid.uuid4())
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

        self.current_file = None

        self.scene = QGraphicsScene()
        self.view = TreeGraphicsView(self.scene)

        #! --------MENU---------
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        new_act = QAction("New", self); new_act.triggered.connect(self.new_tree)
        open_act = QAction("Open", self); open_act.triggered.connect(self.open_tree)
        save_act = QAction("Save", self); save_act.triggered.connect(self.save_tree)
        save_as_act = QAction("Save As...", self); save_as_act.triggered.connect(self.save_tree_as)
        
        file_menu.addAction(new_act)
        file_menu.addAction(open_act)
        file_menu.addSeparator()
        file_menu.addAction(save_act)
        file_menu.addAction(save_as_act)

        #! --------END MENU-----

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

    def new_tree(self):
        if self.scene.items():
            res = QMessageBox.question(self, "Новый файл", "Очистить дерево? Несохраненные данные будут потеряны.")
            if res != QMessageBox.StandardButton.Yes: return
        self.scene.clear()
        self.current_file = None
        self.start_btn.show()
        self.view.hide()
        self.action_panel.hide()

    def save_tree(self):
        if not self.current_file:
            self.save_tree_as()
        else:
            self.perform_save(self.current_file)

    def save_tree_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить дерево", "", "Family Tree (*.ftree)")
        if path:
            if not path.endswith('.ftree'): path += '.ftree'
            self.current_file = path
            self.perform_save(path)

    def perform_save(self, path):
        data = {"people": [], "marriages": [], "child_links": []}
        
        items = self.scene.items()
        people = [i for i in items if isinstance(i, PersonNode)]
        marriages = [i for i in items if isinstance(i, MarriageItem)]
        
        for p in people:
            data["people"].append({
                "id": p.id, "x": p.x(), "y": p.y(), "level": p.level, "is_manual": p.is_manual,
                "first_name": p.data.first_name, "last_name": p.data.last_name,
                "patronymic": p.data.patronymic, "bio": p.data.bio
            })
            
        for m in marriages:
            data["marriages"].append({
                "id": m.id, "node1_id": m.node1.id, "node2_id": m.node2.id
            })

        for i in items:
            if isinstance(i, ChildEdge):
                source_id = i.source.id
                data["child_links"].append({
                    "source_id": source_id, "child_id": i.child_node.id
                })

        with zipfile.ZipFile(path, 'w') as zf:
            zf.writestr('tree.json', json.dumps(data, ensure_ascii=False, indent=4))
            # Здесь в будущем: zf.write(photo_path, 'photos/...')
        self.statusBar().showMessage(f"Сохранено: {path}", 3000)

    def open_tree(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть дерево", "", "Family Tree (*.ftree)")
        if not path: return
        
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                content = zf.read('tree.json')
                data = json.loads(content)
                
            self.scene.clear()
            self.current_file = path
            nodes_map = {}
            marriages_map = {}

            # 1. Создаем людей
            for p_data in data["people"]:
                d = PersonData(p_data["first_name"], p_data["last_name"], p_data["patronymic"], bio=p_data["bio"])
                node = PersonNode(d, p_data["level"], p_data["id"])
                node.setPos(p_data["x"], p_data["y"])
                node.is_manual = p_data["is_manual"]
                self.scene.addItem(node)
                nodes_map[node.id] = node

            # 2. Создаем браки
            for m_data in data["marriages"]:
                n1, n2 = nodes_map[m_data["node1_id"]], nodes_map[m_data["node2_id"]]
                m_item = MarriageItem(n1, n2, m_data["id"])
                self.scene.addItem(m_item)
                n1.links.append(m_item); n2.links.append(m_item)
                marriages_map[m_item.id] = m_item

            # 3. Создаем связи с детьми
            for l_data in data["child_links"]:
                source = nodes_map.get(l_data["source_id"]) or marriages_map.get(l_data["source_id"])
                child = nodes_map[l_data["child_id"]]
                edge = ChildEdge(source, child)
                self.scene.addItem(edge)
                child.links.append(edge)
                if isinstance(source, MarriageItem): source.child_edges.append(edge)
                else: source.links.append(edge)

            self.start_btn.hide()
            self.view.show()
            self.rearrange()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл: {e}")

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
        child_groups = {}  # {source_item: [child_node1, ...]}
        parent_groups = {} # {child_node: [parent_node1, ...]}
        
        for item in self.scene.items():
            if isinstance(item, ChildEdge):
                # Если source - это MarriageItem или PersonNode, это связь "вниз"
                child_groups.setdefault(item.source, []).append(item.child_node)
                # Связь "вверх" (родители для ребенка)
                if isinstance(item.source, PersonNode):
                    parent_groups.setdefault(item.child_node, []).append(item.source)

        spacing = 160 # Расстояние между центрами карточек

        # --- Центрируем детей относительно родителей/браков ---
        for source, children in child_groups.items():
            # Находим X центра источника
            if isinstance(source, MarriageItem):
                target_x = source.get_center().x()
            else:
                target_x = source.sceneBoundingRect().center().x()
            
            # Расставляем детей симметрично (если они не перемещены вручную)
            children.sort(key=lambda c: c.x()) # Сохраняем текущий порядок
            n = len(children)
            start_x = target_x - (n - 1) * spacing / 2
            for i, child in enumerate(children):
                if not child.is_manual:
                    child.setPos(start_x + i * spacing, child.level * 150)

        # --- Центрируем родителей относительно ребенка ---
        for child, parents in parent_groups.items():
            if len(parents) > 0:
                target_x = child.sceneBoundingRect().center().x()
                parents.sort(key=lambda p: p.x())
                n = len(parents)
                start_x = target_x - (n - 1) * spacing / 2
                for i, parent in enumerate(parents):
                    if not parent.is_manual:
                        parent.setPos(start_x + i * spacing, parent.level * 150)

        # 2. Устраняем наложения (Collision Resolution)
        # Теперь, когда семьи сгруппированы, раздвигаем ветки, если они наползли друг на друга
        levels = {}
        for item in self.scene.items():
            if isinstance(item, PersonNode):
                levels.setdefault(item.level, []).append(item)

        for lvl in sorted(levels.keys()):
            nodes = sorted(levels[lvl], key=lambda n: n.x())
            for i in range(len(nodes) - 1):
                curr_node = nodes[i]
                next_node = nodes[i+1]
                if next_node.x() < curr_node.x() + spacing:
                    # Двигаем не только этот узел, но и потенциально всю его ветку 
                    # (хотя для микро-фикса достаточно просто сдвинуть узел)
                    next_node.setPos(curr_node.x() + spacing, next_node.y())

        # 3. Финальное обновление всех линий
        for item in self.scene.items():
            if hasattr(item, 'update_position'):
                item.update_position()
    
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
            # self.link_parent_child_btn.setVisible(True) # Связать двух людей как род-реб
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
        selected = self.scene.selectedItems()
        if not selected: return
        sel = selected[0]
        
        d = PersonDialog()
        if d.exec():
            # Вычисляем уровень
            if isinstance(sel, PersonNode):
                lvl = sel.level - 1 if is_parent else sel.level + 1
            else: # Это MarriageItem
                lvl = sel.node1.level + 1
                
            new_node = PersonNode(d.data, lvl)
            self.scene.addItem(new_node)

            # Начальная позиция точно под/над источником
            source_center_x = sel.sceneBoundingRect().center().x() if isinstance(sel, PersonNode) else sel.get_center().x()
            new_node.setPos(source_center_x, lvl * 150)
            
            # Создаем связь
            edge = ChildEdge(sel, new_node) if not is_parent else ChildEdge(new_node, sel)
            self.scene.addItem(edge)
            
            new_node.links.append(edge)
            if isinstance(sel, MarriageItem): 
                sel.child_edges.append(edge)
            else: 
                sel.links.append(edge)
            
            self.scene.clearSelection()
            # rearrange расставит всех детей по центру красиво
            self.rearrange()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())