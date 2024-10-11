from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsFields,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsSpatialIndex
)
import processing

# Get the project instance
project = QgsProject.instance()

for layer in QgsProject.instance().mapLayers().values():
    print(layer.name())
    
# List of layers by name
layers = [
    project.mapLayer(project.mapLayersByName('scm-10-24-geocoded-cleaned')[0].id()),
    project.mapLayer(project.mapLayersByName('rep-addresses-geocoded')[0].id()),
]

# Define your filter expression
expression = '"state" = \'IL\''  # Change this to your field and filter value

# Apply the filter (subset) to each layer
for layer in layers:
    if layer:
        layer.setSubsetString(expression)
        print(f"Applied filter to {layer.name()}")
    else:
        print(f"Layer not found")
