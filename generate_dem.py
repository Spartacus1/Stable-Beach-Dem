
import os
from qgis.core import (QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem, 
                       QgsRasterLayer, QgsVectorFileWriter, QgsRasterFileWriter)

# Function to set CRS of layers to match the DEM's CRS
def set_layer_crs(layer, crs):
    if layer is not None and isinstance(crs, QgsCoordinateReferenceSystem):
        layer.setCrs(crs)

from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.core import (QgsRasterLayer, QgsPointXY, QgsVectorLayer, 
                      QgsCoordinateReferenceSystem, QgsRectangle, 
                      QgsRasterFileWriter, QgsRaster, QgsGeometry,
                      QgsVectorFileWriter, QgsField, QgsFields, QgsWkbTypes,
                      QgsFeature, QgsCoordinateTransformContext, QgsProcessingFeedback,
                      QgsProject)
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from PyQt5.QtCore import QCoreApplication, QVariant
import numpy as np
import math
import traceback
from osgeo import gdal, ogr
from processing.core.Processing import Processing
import processing
import os


def get_elevation_at_point(point, dem_provider, no_data):
    try:
        # Identificar valor usando o mesmo método dos perfis
        result = dem_provider.identify(point, QgsRaster.IdentifyFormatValue).results()
        if result and 1 in result:
            value = result[1]
            if value != no_data and isinstance(value, (int, float)):
                return float(value)
            
        print(f"No valid elevation at point ({point.x()}, {point.y()})")
        return None
        
    except Exception as e:
        print(f"Error getting elevation at point ({point.x()}, {point.y()}): {str(e)}")
        return None


def create_mask_polygon(output_path, points_layer):
    """
    Cria um polígono conectando os pontos pelo vertex_ind
    """
    try:
        base_path = os.path.splitext(output_path)[0]
        mask_path = f"{base_path}_mask.shp"
        
        # Criar campos para a camada de polígono
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        
        # Criar writer para o shapefile de polígono
        writer = QgsVectorFileWriter(
            mask_path, 'UTF-8', fields, QgsWkbTypes.Polygon,
            points_layer.crs(), 'ESRI Shapefile'
        )
        
        # Verificar se o campo vertex_ind existe
        field_index = points_layer.fields().indexOf('vertex_ind')  # Corrigido aqui
        if field_index == -1:
            print("Field 'vertex_ind' not found in layer")
            for field in points_layer.fields():
                print(f"Available field: {field.name()}")
            return None
        
        # Obter todos os pontos e ordená-los por vertex_ind
        points = []
        for feature in points_layer.getFeatures():
            vertex_ind = feature.attributes()[field_index]  # Corrigido aqui
            if vertex_ind is not None:
                points.append({
                    'vertex_ind': vertex_ind,
                    'point': feature.geometry().asPoint()
                })
                print(f"Added point with vertex_ind: {vertex_ind}")
        
        # Verificar se temos pontos
        if not points:
            print("No points found to create mask")
            return None
            
        # Ordenar pontos por vertex_ind
        points.sort(key=lambda x: x['vertex_ind'])
        print(f"Sorted {len(points)} points")
        
        # Criar lista de pontos para o polígono
        polygon_points = []
        for point_data in points:
            polygon_points.append(point_data['point'])
            print(f"Adding point to polygon: {point_data['point'].x()}, {point_data['point'].y()}")
        
        # Fechar o polígono adicionando o primeiro ponto novamente
        if polygon_points:
            polygon_points.append(polygon_points[0])
            print("Closed polygon by adding first point")
        
        # Criar feature do polígono
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
        feat.setAttributes([1])  # ID do polígono
        result = writer.addFeature(feat)
        print(f"Feature added to writer: {result}")
        
        del writer
        
        # Carregar a camada no projeto
        mask_layer = QgsVectorLayer(mask_path, os.path.splitext(os.path.basename(mask_path))[0], 'ogr')
        if mask_layer.isValid():
            QgsProject.instance().addMapLayer(mask_layer)
            print(f"Mask layer created and loaded successfully: {mask_path}")
        else:
            print("Error loading mask layer")
        
        return mask_path
        
    except Exception as e:
        print(f"Error creating mask polygon: {str(e)}")
        print(traceback.format_exc())
        return None


def create_profile_points_layer(output_path, profiles_data, crs, dem_provider, no_data):
    """
    Cria uma camada de pontos com as elevações inicial e final dos perfis
    """
    base_path = os.path.splitext(output_path)[0]
    points_path = f"{base_path}_profile_points.shp"
    
    fields = QgsFields()
    fields.append(QgsField('ProfNumb', QVariant.Int))
    fields.append(QgsField('PointType', QVariant.String))
    fields.append(QgsField('Elevation', QVariant.Double, 'double', 10, 3))
    fields.append(QgsField('X', QVariant.Double, 'double', 10, 3))
    fields.append(QgsField('Y', QVariant.Double, 'double', 10, 3))
    fields.append(QgsField('vertex_ind', QVariant.Int))  # Nova coluna
    
    writer = QgsVectorFileWriter(
        points_path, 'UTF-8', fields, QgsWkbTypes.Point,
        crs, 'ESRI Shapefile'
    )
    
    # Carregar o shapefile dos perfis para obter as elevações finais
    profiles_path = f"{base_path}_input_dem_profile_points.shp"
    profiles_layer = QgsVectorLayer(profiles_path, "temp_profiles", "ogr")
    
    # Armazenar temporariamente os pontos para ordenação
    start_points = []
    end_points = []
    
    # Primeiro, coletar todos os pontos
    for i, (start_point, end_point) in enumerate(profiles_data, 1):
        # Ponto inicial
        start_elev = get_elevation_at_point(start_point, dem_provider, no_data)
        start_points.append({
            'point': start_point,
            'profnum': i,
            'elev': start_elev if start_elev is not None else no_data,
            'y': start_point.y()
        })
        
        # Ponto final
        profile_features = profiles_layer.getFeatures(f"ProfNumb = {i}")
        profile_feat = next(profile_features)
        end_elev = profile_feat['FinElev']
        end_points.append({
            'point': end_point,
            'profnum': i,
            'elev': end_elev,
            'y': end_point.y()
        })
    
    # Ordenar pontos iniciais por Y (de baixo para cima)
    start_points.sort(key=lambda x: x['y'])
    # Ordenar pontos finais por Y (de cima para baixo)
    end_points.sort(key=lambda x: x['y'], reverse=True)
    
    # Criar features com vertex_ind
    vertex_ind = 1
    
    # Adicionar pontos iniciais
    for point_data in start_points:
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(point_data['point']))
        feat.setAttributes([
            point_data['profnum'],
            'Start',
            point_data['elev'],
            point_data['point'].x(),
            point_data['point'].y(),
            vertex_ind
        ])
        writer.addFeature(feat)
        vertex_ind += 1
    
    # Adicionar pontos finais
    for point_data in end_points:
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(point_data['point']))
        feat.setAttributes([
            point_data['profnum'],
            'End',
            point_data['elev'],
            point_data['point'].x(),
            point_data['point'].y(),
            vertex_ind
        ])
        writer.addFeature(feat)
        vertex_ind += 1
    
    del writer
    
    # Carregar a camada no projeto
    points_layer = QgsVectorLayer(points_path, os.path.splitext(os.path.basename(points_path))[0], 'ogr')
    QgsProject.instance().addMapLayer(points_layer)
    
    # Criar a máscara de polígono
    mask_path = create_mask_polygon(output_path, points_layer)
    
    return points_path, mask_path



def interpolate_points_by_distance(geometry, distance):
    """
    Generate points along a line geometry at regular intervals
    """
    points = []
    
    if geometry.isMultipart():
        lines = geometry.asMultiPolyline()
    else:
        lines = [geometry.asPolyline()]
    
    for line in lines:
        total_length = 0
        for i in range(len(line) - 1):
            segment = QgsGeometry.fromPolylineXY([QgsPointXY(line[i]), QgsPointXY(line[i + 1])])
            total_length += segment.length()
        
        num_intervals = max(int(total_length / distance), 1)
        
        for i in range(num_intervals + 1):
            dist_along = (i * total_length) / num_intervals if i < num_intervals else total_length
            
            current_dist = 0
            for j in range(len(line) - 1):
                segment = QgsGeometry.fromPolylineXY([QgsPointXY(line[j]), QgsPointXY(line[j + 1])])
                segment_length = segment.length()
                
                if current_dist + segment_length >= dist_along:
                    segment_fraction = (dist_along - current_dist) / segment_length
                    x = line[j].x() + (line[j + 1].x() - line[j].x()) * segment_fraction
                    y = line[j].y() + (line[j + 1].y() - line[j].y()) * segment_fraction
                    points.append(QgsPointXY(x, y))
                    break
                
                current_dist += segment_length
    
    return points

def get_profile_points(geometry, interval=None):
    """
    Get points along the line either by nodes or by distance interval
    """
    if interval is None or interval <= 0:
        # Node-based method
        if geometry.isMultipart():
            points = [QgsPointXY(p) for line in geometry.asMultiPolyline() for p in line]
        else:
            points = [QgsPointXY(p) for p in geometry.asPolyline()]
    else:
        # Distance-based method
        points = interpolate_points_by_distance(geometry, interval)
    
    print(f"Generated {len(points)} profile points")
    return points

def find_closest_point_on_line(point, line_geometry):
    """
    Encontra o ponto mais próximo na linha B para um dado ponto da linha A
    """
    closest_point = line_geometry.nearestPoint(QgsGeometry.fromPointXY(point))
    return closest_point.asPoint()

def calculate_direction(point_a, point_b):
    """
    Calcula a direção entre dois pontos em graus (0 = Norte, 90 = Leste)
    """
    dx = point_b.x() - point_a.x()
    dy = point_b.y() - point_a.y()
    angle = math.degrees(math.atan2(dx, dy))
    if angle < 0:
        angle += 360
    return angle

def calculate_profile_azimuth(start_point, end_point):
    """
    Calcula o azimute do perfil em graus (0-360)
    """
    dx = end_point.x() - start_point.x()
    dy = end_point.y() - start_point.y()
    angle = math.degrees(math.atan2(dx, dy))
    if angle < 0:
        angle += 360
    return angle

def calculate_profile_length(start_point, end_point):
    """
    Calcula o comprimento do perfil em metros
    """
    dx = end_point.x() - start_point.x()
    dy = end_point.y() - start_point.y()
    return math.sqrt(dx * dx + dy * dy)

def create_profiles_shapefile(output_path, profiles_data, crs, dem_provider, no_data, slope=None):
    """
    Cria um shapefile com as linhas dos perfis e seus atributos
    """
    try:
        print("Starting profiles shapefile creation...")
        
        base_path = os.path.splitext(output_path)[0]
        profiles_path = f"{base_path}_input_dem_profile_points.shp"
        print(f"Profiles will be saved to: {profiles_path}")
        
        # Remover arquivos existentes
        for ext in ['.shp', '.shx', '.dbf', '.prj']:
            old_file = f"{base_path}_profiles{ext}"
            if os.path.exists(old_file):
                try:
                    os.remove(old_file)
                    print(f"Removed existing file: {old_file}")
                except Exception as e:
                    print(f"Warning: Could not remove existing file {old_file}: {str(e)}")
        
        # Criar campos com precisão específica para controlar as casas decimais
        fields = QgsFields()
        fields.append(QgsField('ProfNumb', QVariant.Int))
        fields.append(QgsField('ProfileAz', QVariant.Double, 'double', 10, 3))
        fields.append(QgsField('IniElev', QVariant.Double, 'double', 10, 3))
        fields.append(QgsField('FinElev', QVariant.Double, 'double', 10, 3))
        fields.append(QgsField('Dist_profile', QVariant.Double, 'double', 10, 3))
        
        # Criar layer em memória primeiro
        memory_layer = QgsVectorLayer("LineString?crs=" + crs.authid(), "profiles", "memory")
        memory_provider = memory_layer.dataProvider()
        memory_provider.addAttributes(fields.toList())
        memory_layer.updateFields()
        
        # Adicionar features
        features = []
        for i, (start_point, end_point) in enumerate(profiles_data, start=1):
            # Verificar se os pontos são válidos
            if not (start_point and end_point):
                print(f"Warning: Invalid points for profile {i}")
                continue
                
            # Criar geometria
            line_geom = QgsGeometry.fromPolylineXY([start_point, end_point])
            if not line_geom.isGeosValid():
                print(f"Warning: Invalid geometry for profile {i}")
                continue
            
            # Obter elevações com validação extra
            ini_elev = get_elevation_at_point(start_point, dem_provider, no_data)
            fin_elev = get_elevation_at_point(end_point, dem_provider, no_data)
            
            if ini_elev is None:
                print(f"Warning: No initial elevation for profile {i}")
                ini_elev = no_data
            if fin_elev is None:
                if slope is not None and ini_elev != no_data:
                    distance = calculate_profile_length(start_point, end_point)
                    fin_elev = ini_elev - (distance * math.tan(math.radians(slope)))
                else:
                    fin_elev = no_data
            
            # Calcular outros atributos
            profile_az = calculate_profile_azimuth(start_point, end_point)
            dist_profile = calculate_profile_length(start_point, end_point)
            
            # Criar e configurar feature
            feat = QgsFeature()
            feat.setGeometry(line_geom)
            feat.setAttributes([
                i,                              # ProfNumb
                float(round(profile_az, 3)),    # ProfileAz
                float(round(ini_elev, 3)),      # IniElev
                float(round(fin_elev, 3)),      # FinElev
                float(round(dist_profile, 3))   # Dist_profile
            ])
            
            features.append(feat)
        
        # Adicionar todas as features à camada em memória
        memory_provider.addFeatures(features)
        
        # Salvar como shapefile
        print(f"Saving {len(features)} features to shapefile...")
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "ESRI Shapefile"
        options.fileEncoding = "UTF-8"
        options.layerOptions = ['DECIMAL_POINT=.']
        
        write_result = QgsVectorFileWriter.writeAsVectorFormat(
            memory_layer,
            profiles_path,
            "UTF-8",
            crs,
            "ESRI Shapefile",
            layerOptions=['DECIMAL_POINT=.']
        )
        
        if write_result[0] != QgsVectorFileWriter.NoError:
            raise Exception(f"Error saving shapefile: {write_result}")

        print(f"Shapefile created successfully with {len(features)} profiles!")
        return profiles_path

    except Exception as e:
        print(f"Error in create_profiles_shapefile: {str(e)}")
        print(traceback.format_exc())
        return None

def generate_stable_beach_dem(dem_layer, line_a, line_b, slope, output_path, distance_interval=None):
    try:
        print("Starting DEM generation process")
        if distance_interval:
            print(f"Using distance-based interval: {distance_interval}m")
        else:
            print("Using node-based profiles")
            
        provider = dem_layer.dataProvider()
        dem_extent = dem_layer.extent()
        pixel_size_x = dem_extent.width() / provider.xSize()
        pixel_size_y = dem_extent.height() / provider.ySize()

        no_data = provider.sourceNoDataValue(1) or -9999.0
        print(f"Using NoData value: {no_data}")

        # Get geometries
        line_a_geom = list(line_a.getFeatures())[0].geometry()
        line_b_geom = list(line_b.getFeatures())[0].geometry()

        # Get profile points based on selected method
        profile_points = get_profile_points(line_a_geom, distance_interval)
        print(f"Generated {len(profile_points)} profile points")

        # Compute extent and dimensions
        bbox = line_a_geom.boundingBox()
        bbox.combineExtentWith(line_b_geom.boundingBox())
        cols = max(int((bbox.xMaximum() - bbox.xMinimum()) / pixel_size_x), 1)
        rows = max(int((bbox.yMaximum() - bbox.yMinimum()) / pixel_size_y), 1)

        result_array = np.full((rows, cols), no_data, dtype=np.float32)
        
        slope_radians = math.radians(slope)
        step_size = math.sqrt(pixel_size_x**2 + pixel_size_y**2)
        elevation_step = math.tan(slope_radians) * step_size

        # Lista para armazenar perfis
        lines_for_shp = []

        # Process each profile point
        for start_point in profile_points:
            # Get elevation at start point
            elevation = get_elevation_at_point(start_point, provider, no_data)
            if elevation == no_data:
                continue

            # Convert to raster coordinates
            col = int((start_point.x() - bbox.xMinimum()) / pixel_size_x)
            row = int((bbox.yMaximum() - start_point.y()) / pixel_size_y)
            
            # Find closest point on Line B
            end_point = find_closest_point_on_line(start_point, line_b_geom)
            lines_for_shp.append((start_point, end_point))
            
            # Calculate direction for this specific profile
            direction = calculate_direction(start_point, end_point)
            direction_radians = math.radians((450 - direction) % 360)
            
            # Calculate direction vector
            dx = math.cos(direction_radians) * step_size
            dy = -math.sin(direction_radians) * step_size

            # Interpolate profile
            current_elevation = elevation
            current_row = float(row)
            current_col = float(col)
            steps = 0
            max_steps = int(math.sqrt(cols**2 + rows**2))

            while steps < max_steps:
                if not (0 <= int(round(current_row)) < rows and 
                       0 <= int(round(current_col)) < cols):
                    break

                # Check if we reached line B
                world_x = bbox.xMinimum() + current_col * pixel_size_x
                world_y = bbox.yMaximum() - current_row * pixel_size_y
                current_point = QgsPointXY(world_x, world_y)
                if line_b_geom.distance(QgsGeometry.fromPointXY(current_point)) < pixel_size_x:
                    break

                # Update raster values
                r = int(round(current_row))
                c = int(round(current_col))
                if result_array[r, c] == no_data:
                    result_array[r, c] = current_elevation

                # Fill surrounding pixels to avoid gaps
                for r_offset in [-1, 0, 1]:
                    for c_offset in [-1, 0, 1]:
                        new_row = r + r_offset
                        new_col = c + c_offset
                        if (0 <= new_row < rows and 
                            0 <= new_col < cols and 
                            result_array[new_row, new_col] == no_data):
                            result_array[new_row, new_col] = current_elevation

                current_elevation -= elevation_step
                current_row += dy / pixel_size_y
                current_col += dx / pixel_size_x
                steps += 1

        # Save the DEM raster
        driver = gdal.GetDriverByName('GTiff')
        out_raster = driver.Create(output_path, cols, rows, 1, gdal.GDT_Float32)
        geotransform = [
            bbox.xMinimum(), pixel_size_x, 0,
            bbox.yMaximum(), 0, -pixel_size_y
        ]
        out_raster.SetGeoTransform(geotransform)
        out_raster.SetProjection(dem_layer.crs().toWkt())
        out_band = out_raster.GetRasterBand(1)
        out_band.SetNoDataValue(no_data)
        out_band.WriteArray(result_array)
        out_band.FlushCache()
        out_raster = None

        # Criar shapefile dos perfis
        print(f"Number of profiles to create: {len(lines_for_shp)}")
        profiles_path = None
        if lines_for_shp:
            try:
                profiles_path = create_profiles_shapefile(
                    output_path, 
                    lines_for_shp, 
                    dem_layer.crs(),
                    provider,
                    no_data,
                    slope
                )
                if profiles_path:
                    print(f"Profiles shapefile created at: {profiles_path}")
                    # Criar camada de pontos e máscara
                    points_path, mask_path = create_profile_points_layer(
                        output_path,
                        lines_for_shp,
                        dem_layer.crs(),
                        provider,
                        no_data
                    )
                    print(f"Points layer created at: {points_path}")
                    print(f"Mask layer created at: {mask_path}")
                else:
                    print("Failed to create profiles shapefile")
            except Exception as e:
                print(f"Error creating profiles shapefile: {str(e)}")
                print(traceback.format_exc())

        print("DEM generation completed!")
        return True, "DEM generated successfully!", profiles_path

    except Exception as e:
        print(traceback.format_exc())
        return False, f"Error: {str(e)}", None

def interpolate_surface(input_dem_path, output_surface_path, mode='wmean', power=2.0, cells=6, distance=0.5, no_nulls=True):
    """
    Interpola uma superfície contínua usando r.fill.stats do GRASS
    """
    try:
        print("Starting surface interpolation...")
        print(f"Parameters: mode={mode}, power={power}, cells={cells}, distance={distance}")
        
        # Converter modo para número conforme r.fill.stats
        mode_map = {'wmean': 0, 'mean': 1, 'median': 2, 'mode': 3}
        mode_num = mode_map.get(mode, 0)  # default para wmean se modo inválido
        
        params = {
            'input': input_dem_path,
            'output': output_surface_path,
            'mode': mode_num,
            'power': power,
            'cells': cells,
            'distance': distance,
            '-n': no_nulls,
            'GRASS_REGION_PARAMETER': None,
            'GRASS_REGION_CELLSIZE_PARAMETER': 0,
            'GRASS_RASTER_FORMAT_OPT': '',
            'GRASS_RASTER_FORMAT_META': ''
        }
        
        feedback = QgsProcessingFeedback()
        result = processing.run("grass7:r.fill.stats", params, feedback=feedback)
        print("Surface interpolation completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error in surface interpolation: {str(e)}")
        print(traceback.format_exc())
        return False
        
def crop_surface_with_mask(surface_path, mask_path):
    """
    Recorta a superfície usando a máscara do polígono
    """
    try:
        base_path = os.path.splitext(surface_path)[0]
        cropped_path = f"{base_path}_cropped.tif"
        
        # Obter o valor NoData da camada original
        original_layer = QgsRasterLayer(surface_path)
        no_data = original_layer.dataProvider().sourceNoDataValue(1)
        
        params = {
            'INPUT': surface_path,
            'MASK': mask_path,
            'SOURCE_CRS': None,
            'TARGET_CRS': None,
            'NODATA': no_data,  # Usar o mesmo valor NoData da camada original
            'ALPHA_BAND': False,
            'CROP_TO_CUTLINE': True,
            'KEEP_RESOLUTION': True,
            'SET_MASK_NO_DATA': True,  # Definir valores fora da máscara como NoData
            'OPTIONS': '',
            'DATA_TYPE': 0,
            'OUTPUT': cropped_path
        }
        
        print("Starting surface cropping...")
        print(f"Using NoData value: {no_data}")
        result = processing.run("gdal:cliprasterbymasklayer", params)
        
        # Carregar a camada recortada
        cropped_layer = QgsRasterLayer(cropped_path, os.path.splitext(os.path.basename(cropped_path))[0])
        if cropped_layer.isValid():
            QgsProject.instance().addMapLayer(cropped_layer)
            print(f"Cropped surface created and loaded successfully: {cropped_path}")
            return cropped_path
        else:
            print("Error loading cropped surface")
            return None
            
    except Exception as e:
        print(f"Error cropping surface: {str(e)}")
        print(traceback.format_exc())
        return None