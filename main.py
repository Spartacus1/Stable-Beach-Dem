from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QAction, 
    QDialog, 
    QFileDialog, 
    QProgressBar, 
    QVBoxLayout,
    QLabel
)
from qgis.core import (
    QgsProject, 
    QgsRasterLayer, 
    QgsVectorLayer,
    QgsWkbTypes,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsVectorFileWriter
)
from qgis.PyQt.QtCore import QVariant
from .form import Ui_Form
from .generate_dem import generate_stable_beach_dem, interpolate_surface, crop_surface_with_mask
from .volume_calculation_grid import generate_grid, find_mask_layer
from qgis.PyQt import QtCore
import os

class DEMGenerationThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, dem_layer, line_a, line_b, slope, output_path, distance_interval=None, interpolate=False,
                 power=2.0, cells=6, distance=0.5, mode='wmean', no_nulls=True):
        super().__init__()
        self.dem_layer = dem_layer
        self.line_a = line_a
        self.line_b = line_b
        self.slope = slope
        self.output_path = output_path
        self.distance_interval = distance_interval
        self.interpolate = interpolate
        self.power = power
        self.cells = cells
        self.distance = distance
        self.mode = mode
        self.no_nulls = no_nulls
        print(f"Thread initialized with output path: {output_path}")

    def run(self):
        print("Starting DEM generation process")
        self.status.emit("Starting DEM generation...")
        self.progress.emit(10)
        
        try:
            self.status.emit("Generating DEM...")
            self.progress.emit(30)
            
            success, message, profiles_path = generate_stable_beach_dem(
                self.dem_layer, 
                self.line_a, 
                self.line_b, 
                self.slope,
                self.output_path,
                self.distance_interval
            )
            
            if success and self.interpolate:
                self.status.emit("Interpolating surface...")
                surface_path = f"{os.path.splitext(self.output_path)[0]}_surface.tif"
                
                interpolation_success = interpolate_surface(
                    self.output_path,
                    surface_path,
                    mode=self.mode,
                    power=self.power,
                    cells=self.cells,
                    distance=self.distance,
                    no_nulls=self.no_nulls
                )
                
                if interpolation_success:
                    mask_path = f"{os.path.splitext(self.output_path)[0]}_mask.shp"
                    if os.path.exists(mask_path):
                        cropped_path = crop_surface_with_mask(surface_path, mask_path)
                        if cropped_path:
                            print(f"Surface cropped successfully: {cropped_path}")
                        else:
                            print("Error during surface cropping")
                else:
                    print("Warning: Error during surface interpolation")
                    self.status.emit("Warning: Error during surface interpolation")
            
            self.progress.emit(90)
            self.status.emit("Finalizing...")
            
            if os.path.exists(self.output_path):
                layer_name = os.path.splitext(os.path.basename(self.output_path))[0]
                layer = QgsRasterLayer(self.output_path, layer_name)
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
                    
                    if self.interpolate:
                        surface_path = f"{os.path.splitext(self.output_path)[0]}_surface.tif"
                        if os.path.exists(surface_path):
                            surface_layer = QgsRasterLayer(surface_path, os.path.splitext(os.path.basename(surface_path))[0])
                            if surface_layer.isValid():
                                QgsProject.instance().addMapLayer(surface_layer)
                    
                    if profiles_path and os.path.exists(profiles_path):
                        profiles_layer = QgsVectorLayer(profiles_path, f"{layer_name}_profiles", "ogr")
                        if profiles_layer.isValid():
                            QgsProject.instance().addMapLayer(profiles_layer)
                            if self.interpolate:
                                self.status.emit("DEM, surface and profiles loaded successfully in QGIS.")
                            else:
                                self.status.emit("DEM and profiles loaded successfully in QGIS.")
                        else:
                            self.status.emit("Raster layers loaded, but error loading profiles in QGIS.")
                    else:
                        self.status.emit("Raster layers loaded, but profiles file not found.")
                else:
                    self.status.emit("Error loading DEM in QGIS.")
            else:
                self.status.emit("Error: file not found after processing.")

            self.progress.emit(100)
            self.finished.emit(success, message)
            
        except Exception as e:
            print(f"Error in thread: {str(e)}")
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(False, str(e))


class VolumeGridThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, polygon_layer, grid_size):
        super().__init__()
        self.polygon_layer = polygon_layer
        self.grid_size = grid_size
        
    def run(self):
        try:
            self.status.emit("Starting grid generation...")
            self.progress.emit(10)
            
            # Encontrar a máscara existente
            mask_layer = find_mask_layer()
            if not mask_layer:
                self.status.emit("No mask layer found")
                self.finished.emit(False, "No mask layer found")
                return
                
            # Get the extent of the polygon layer
            extent = self.polygon_layer.extent()
            
            # Calculate number of cells in each direction
            cols = int((extent.xMaximum() - extent.xMinimum()) / self.grid_size)
            rows = int((extent.yMaximum() - extent.yMinimum()) / self.grid_size)
            
            self.status.emit(f"Creating grid with {rows}x{cols} cells...")
            self.progress.emit(30)
            
            # Create a new memory layer for the grid
            grid_layer = QgsVectorLayer("Polygon", "calculation_grid", "memory")
            provider = grid_layer.dataProvider()
            
            # Add fields for the grid
            provider.addAttributes([
                QgsField("id", QVariant.Int),
                QgsField("centroid_x", QVariant.Double),
                QgsField("centroid_y", QVariant.Double),
                QgsField("area", QVariant.Double)
            ])
            grid_layer.updateFields()
            
            # Create grid cells
            features = []
            cell_id = 1
            
            for row in range(rows):
                self.progress.emit(30 + int(60 * row / rows))
                for col in range(cols):
                    # Calculate cell coordinates
                    x_min = extent.xMinimum() + col * self.grid_size
                    x_max = x_min + self.grid_size
                    y_min = extent.yMinimum() + row * self.grid_size
                    y_max = y_min + self.grid_size
                    
                    # Create cell geometry
                    points = [
                        QgsPointXY(x_min, y_min),
                        QgsPointXY(x_max, y_min),
                        QgsPointXY(x_max, y_max),
                        QgsPointXY(x_min, y_max),
                        QgsPointXY(x_min, y_min)  # Close the polygon
                    ]
                    
                    # Create feature
                    feat = QgsFeature()
                    feat.setGeometry(QgsGeometry.fromPolygonXY([points]))
                    
                    # Calculate centroid
                    centroid = feat.geometry().centroid().asPoint()
                    
                    # Set attributes
                    feat.setAttributes([
                        cell_id,
                        centroid.x(),
                        centroid.y(),
                        self.grid_size * self.grid_size
                    ])
                    
                    features.append(feat)
                    cell_id += 1
            
            # Add features to layer
            provider.addFeatures(features)
            
            # Save grid layer
            save_path, _ = QFileDialog.getSaveFileName(None, "Save Grid Layer", "", "ESRI Shapefile (*.shp)")
            if save_path:
                # Add .shp extension if not present
                if not save_path.lower().endswith('.shp'):
                    save_path += '.shp'
                    
                # Save the layer
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "ESRI Shapefile"
                error = QgsVectorFileWriter.writeAsVectorFormat(
                    grid_layer,
                    save_path,
                    "UTF-8",
                    self.polygon_layer.crs(),
                    "ESRI Shapefile"
                )
                
                if error[0] == QgsVectorFileWriter.NoError:
                    # Load the saved layer
                    saved_layer = QgsVectorLayer(save_path, "Calculation Grid", "ogr")
                    if saved_layer.isValid():
                        QgsProject.instance().addMapLayer(saved_layer)
                        self.status.emit("Grid layer created and saved successfully")
                        self.finished.emit(True, "Grid generation completed successfully")
                    else:
                        self.status.emit("Error loading saved grid layer")
                        self.finished.emit(False, "Error loading saved grid layer")
                else:
                    self.status.emit("Error saving grid layer")
                    self.finished.emit(False, "Error saving grid layer")
            else:
                # User cancelled save operation
                self.status.emit("Operation cancelled by user")
                self.finished.emit(False, "Operation cancelled by user")
            
            self.progress.emit(100)
            
        except Exception as e:
            print(f"Error in grid generation: {str(e)}")
            self.status.emit(f"Error: {str(e)}")
            self.finished.emit(False, str(e))


class StableBeachDEMPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.thread = None
        self.current_tab = 0

    def initGui(self):
        self.action = QAction("Beach Analysis Tool", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Stable Beach Tool", self.action)

    def unload(self):
        self.iface.removePluginMenu("&Stable Beach Tool", self.action)
        
    def run(self):
        self.dialog = QDialog()
        self.dialog.setWindowFlags(self.dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.ui = Ui_Form()
        self.ui.setupUi(self.dialog)
        self.populate_layers()
        
        # Connect tab change signal
        self.ui.tabWidget.currentChanged.connect(self.on_tab_changed)
        
        # Connect buttons
        self.ui.runButton.clicked.connect(self.start_processing)
        self.ui.generateGridButton.clicked.connect(self.start_grid_generation)
        
        self.dialog.show()

    def populate_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        
        # Clear all combos
        self.ui.demLayerCombo.clear()
        self.ui.lineALayerCombo.clear()
        self.ui.lineBLayerCombo.clear()
        self.ui.polygonLayerCombo.clear()
        
        # Populate combos based on layer type
        for layer in layers:
            if isinstance(layer, QgsRasterLayer):
                self.ui.demLayerCombo.addItem(layer.name(), layer)
            elif isinstance(layer, QgsVectorLayer):
                if layer.geometryType() == QgsWkbTypes.LineGeometry:
                    self.ui.lineALayerCombo.addItem(layer.name(), layer)
                    self.ui.lineBLayerCombo.addItem(layer.name(), layer)
                elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                    self.ui.polygonLayerCombo.addItem(layer.name(), layer)

    def on_tab_changed(self, index):
        self.current_tab = index
        if index == 0:  # Stable Beach Generation
            self.ui.runButton.setVisible(True)
            self.ui.runButton.setText("Generate DEM")
        else:  # Volume Calculation Grid
            self.ui.runButton.setVisible(False)
            self.populate_polygon_layers()

    def populate_polygon_layers(self):
        """Atualiza apenas o combo box de layers de polígono"""
        self.ui.polygonLayerCombo.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer) and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.ui.polygonLayerCombo.addItem(layer.name(), layer)


    def start_processing(self):
        if self.current_tab == 0:
            self.start_dem_generation()
        else:
            self.start_volume_calculation()

    def start_grid_generation(self):
        """Inicia o processo de geração da grade"""
        try:
            grid_size = float(self.ui.gridSizeInput.text())
            if grid_size <= 0:
                raise ValueError("Grid size must be greater than 0")

            mask_layer = find_mask_layer()
            if not mask_layer:
                self.iface.messageBar().pushMessage(
                    "Error", 
                    "No mask layer found. Please generate a DEM first.", 
                    level=2
                )
                return

            only_overlap = self.ui.overlapCheckBox.isChecked()

            success, message = generate_grid(
                mask_layer=mask_layer,
                cell_size=grid_size,
                only_overlap=only_overlap
            )

            if success:
                self.iface.messageBar().pushMessage("Success", message, level=3)
            else:
                self.iface.messageBar().pushMessage("Error", message, level=2)

        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Error",
                f"Error generating grid: {str(e)}",
                level=2
            )

    def start_dem_generation(self):
        print("\n=== Starting DEM Generation Process ===")
        
        self.ui.runButton.setEnabled(False)
        
        # Get selected layers
        dem_layer = self.ui.demLayerCombo.currentData()
        line_a_layer = self.ui.lineALayerCombo.currentData()
        line_b_layer = self.ui.lineBLayerCombo.currentData()
        
        print(f"Selected layers:")
        print(f"- DEM: {dem_layer.name() if dem_layer else 'None'}")
        print(f"- Line A: {line_a_layer.name() if line_a_layer else 'None'}")
        print(f"- Line B: {line_b_layer.name() if line_b_layer else 'None'}")
        
        try:
            slope = float(self.ui.slopeInput.text())
            print(f"Parameters: Slope={slope}")
        except ValueError as e:
            print(f"Error parsing slope value: {e}")
            self.iface.messageBar().pushMessage("Error", "Invalid slope value", level=2)
            self.ui.runButton.setEnabled(True)
            return

        # Get profile creation method and distance interval if applicable
        distance_interval = None
        if self.ui.distanceIntervalRadio.isChecked():
            try:
                distance_interval = float(self.ui.distanceInput.text())
                if distance_interval <= 0:
                    raise ValueError("Distance must be greater than 0")
                print(f"Using distance interval: {distance_interval}m")
            except ValueError as e:
                print(f"Error parsing distance value: {e}")
                self.iface.messageBar().pushMessage("Error", "Invalid distance value", level=2)
                self.ui.runButton.setEnabled(True)
                return

        if not (dem_layer and line_a_layer and line_b_layer):
            print("Error: Missing input layers")
            self.iface.messageBar().pushMessage("Error", "Please select all input layers.", level=2)
            self.ui.runButton.setEnabled(True)
            return

        output_file, _ = QFileDialog.getSaveFileName(
            self.dialog, 
            "Save DEM", 
            "", 
            "GeoTIFF Files (*.tif)"
        )
        
        print(f"Selected output file: {output_file}")
        
        if not output_file:
            print("Error: No output file selected")
            self.iface.messageBar().pushMessage("Error", "Output file not specified.", level=2)
            self.ui.runButton.setEnabled(True)
            return

        # Get interpolation parameters if enabled
        interpolate = self.ui.interpolateCheckBox.isChecked()
        power = cells = distance = mode = no_nulls = None
        if interpolate:
            try:
                power = float(self.ui.powerInput.text())
                cells = int(self.ui.cellsInput.text())
                distance = float(self.ui.distanceSearchInput.text())
                mode = self.ui.modeCombo.currentText()
                no_nulls = self.ui.noNullsCheckBox.isChecked()
                print(f"Interpolation parameters: mode={mode}, power={power}, cells={cells}, distance={distance}, no_nulls={no_nulls}")
            except ValueError as e:
                print(f"Error parsing interpolation parameters: {e}")
                self.iface.messageBar().pushMessage("Error", "Invalid interpolation parameters", level=2)
                self.ui.runButton.setEnabled(True)
                return

        # Initialize and start the processing thread
        print("Starting processing thread...")
        self.thread = DEMGenerationThread(
            dem_layer, 
            line_a_layer, 
            line_b_layer, 
            slope,
            output_file,
            distance_interval,
            interpolate,
            power,
            cells,
            distance,
            mode,
            no_nulls
        )
        self.thread.progress.connect(self.ui.progressBar.setValue)
        self.thread.status.connect(self.ui.statusLabel.setText)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def start_volume_calculation(self):
        self.ui.runButton.setEnabled(False)
        
        # Get selected polygon layer
        polygon_layer = self.ui.polygonLayerCombo.currentData()
        if not polygon_layer:
            self.iface.messageBar().pushMessage("Error", "Please select a polygon layer", level=2)
            self.ui.runButton.setEnabled(True)
            return
            
        try:
            grid_size = float(self.ui.gridSizeInput.text())
            if grid_size <= 0:
                raise ValueError("Grid size must be greater than 0")
        except ValueError as e:
            self.iface.messageBar().pushMessage("Error", "Invalid grid size value", level=2)
            self.ui.runButton.setEnabled(True)
            return

        # Initialize and start the grid generation thread
        self.thread = VolumeGridThread(polygon_layer, grid_size)
        self.thread.progress.connect(self.ui.progressBar.setValue)
        self.thread.status.connect(self.ui.statusLabel.setText)
        self.thread.finished.connect(self.on_thread_finished)
        self.thread.start()

    def on_thread_finished(self, success, message):
        if success:
            self.iface.messageBar().pushMessage("Success", message, level=0)
        else:
            self.iface.messageBar().pushMessage("Error", message, level=2)
        
        self.ui.progressBar.setValue(0)
        self.ui.statusLabel.setText("Ready")
        self.ui.runButton.setEnabled(True)
        self.thread = None