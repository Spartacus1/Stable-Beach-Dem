from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFields,  # Adicionada esta importação
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsWkbTypes,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem
)
from qgis.PyQt.QtCore import QVariant
import os

def find_mask_layer():
    """Encontra a layer que termina com '_mask' no projeto"""
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.name().endswith('_mask'):
            return layer
    return None

def generate_grid(mask_layer, cell_size, only_overlap=False):
    """
    Gera uma grade de polígonos baseada na extensão da máscara
    """
    try:
        if not mask_layer:
            return False, "Mask layer not found"

        # Obter extensão da máscara
        extent = mask_layer.extent()
        
        # Calcular número de células em cada direção
        cols = int((extent.xMaximum() - extent.xMinimum()) / cell_size) + 1
        rows = int((extent.yMaximum() - extent.yMinimum()) / cell_size) + 1

        # Preparar o nome do arquivo de saída
        base_path = os.path.dirname(mask_layer.source())
        base_name = os.path.splitext(os.path.basename(mask_layer.source()))[0]
        output_path = os.path.join(base_path, f"{base_name}_grid.shp")

        # Definir campos
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("centroid_x", QVariant.Double))
        fields.append(QgsField("centroid_y", QVariant.Double))
        fields.append(QgsField("area", QVariant.Double))

        # Criar writer para o shapefile
        writer = QgsVectorFileWriter(
            output_path,
            "UTF-8",
            fields,
            QgsWkbTypes.Polygon,
            mask_layer.crs(),
            "ESRI Shapefile"
        )

        if writer.hasError() != QgsVectorFileWriter.NoError:
            return False, f"Error creating grid file: {writer.errorMessage()}"

        # Criar células
        cell_id = 1
        mask_geom = next(mask_layer.getFeatures()).geometry()

        features = []  # Lista para armazenar todas as features
        for row in range(rows):
            for col in range(cols):
                # Calcular coordenadas da célula
                x_min = extent.xMinimum() + col * cell_size
                x_max = x_min + cell_size
                y_min = extent.yMinimum() + row * cell_size
                y_max = y_min + cell_size

                # Criar geometria da célula
                points = [
                    QgsPointXY(x_min, y_min),
                    QgsPointXY(x_max, y_min),
                    QgsPointXY(x_max, y_max),
                    QgsPointXY(x_min, y_max),
                    QgsPointXY(x_min, y_min)
                ]
                cell_geom = QgsGeometry.fromPolygonXY([points])

                # Se only_overlap está ativo, verificar interseção
                if only_overlap and not cell_geom.intersects(mask_geom):
                    continue

                # Criar feature
                feat = QgsFeature()
                feat.setGeometry(cell_geom)

                # Calcular centroide
                centroid = cell_geom.centroid().asPoint()

                # Definir atributos
                feat.setAttributes([
                    cell_id,
                    centroid.x(),
                    centroid.y(),
                    cell_size * cell_size
                ])

                # Adicionar feature à lista
                features.append(feat)
                cell_id += 1

        # Adicionar todas as features de uma vez
        writer.addFeatures(features)

        # Limpar o writer
        del writer

        # Carregar a nova camada no QGIS
        grid_layer = QgsVectorLayer(output_path, f"{base_name}_grid", "ogr")
        if grid_layer.isValid():
            QgsProject.instance().addMapLayer(grid_layer)
            return True, "Grid generated successfully"
        else:
            return False, "Error loading generated grid"

    except Exception as e:
        import traceback
        error_msg = f"Error generating grid: {str(e)}\n{traceback.format_exc()}"
        return False, error_msg