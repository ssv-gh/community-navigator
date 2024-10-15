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

# Input layers
points_layer = QgsProject.instance().mapLayersByName('sample-FH-locations')[0]
circles_layer = QgsProject.instance().mapLayersByName('10mi-cn-test')[0]

# Assuming census layers are grouped in a layer group named 'Census_Layers_Group'
census_layer_group_name = 'popstats-by-census-tract-2020'
census_layer_group = QgsProject.instance().layerTreeRoot().findGroup(census_layer_group_name)

# New field names for proportional demographic data
fields_to_recalculate = ['Population Est CrYr', 'Gender Females CrYr', 'Gender Males CrYr', 'Households Est CrYr', 'Eth Hispanic CrYr']  # Replace with your attribute fields
new_field_suffix = '_recalculated'

# Create a new memory layer for the recalculated data
crs = QgsCoordinateReferenceSystem('EPSG:3857')
new_layer = QgsVectorLayer(f"Polygon?crs={crs.toWkt()}", "Recalculated_Census_Tracts", "memory")
new_layer_data_provider = new_layer.dataProvider()

# Add the original fields + new recalculated fields (based on the first census layer)
first_census_layer = census_layer_group.findLayers()[0].layer()
original_fields = first_census_layer.fields()
new_fields = QgsFields()
for field in original_fields:
    new_fields.append(field)
for field in fields_to_recalculate:
    new_fields.append(QgsField(field + new_field_suffix, QVariant.Double))
new_layer_data_provider.addAttributes(new_fields)
new_layer.updateFields()

# Build a spatial index for the circles to quickly identify intersecting census layers
circle_index = QgsSpatialIndex(circles_layer.getFeatures())

# Identify which census layers are relevant based on intersecting circles
relevant_census_layers = set()

for census_layer_node in census_layer_group.findLayers():
    census_layer = census_layer_node.layer()
    
    for census_feature in census_layer.getFeatures():
        census_geom = census_feature.geometry()
        intersecting_circle_ids = circle_index.intersects(census_geom.boundingBox())
        
        if intersecting_circle_ids:
            relevant_census_layers.add(census_layer)
            break  # No need to check further features in this layer

# Process each circle
for circle_feature in circles_layer.getFeatures():
    circle_geom = circle_feature.geometry()
    location_name = circle_feature['LocationNa']
    location_id = circle_feature['LocationID']
    
    # Loop through each relevant census layer
    for census_layer in relevant_census_layers:
        # Loop through intersected census tracts in the current state layer
        for census_feature in census_layer.getFeatures():
            census_geom = census_feature.geometry()
            
            if census_geom.intersects(circle_geom):
                intersected_geom = census_geom.intersection(circle_geom)
                area_ratio = intersected_geom.area() / census_geom.area()
                
                # Create a new feature for the new layer
                new_feature = QgsFeature(new_layer.fields())
                new_feature.setGeometry(intersected_geom)
                
                # Copy over the original attributes
                for field in original_fields:
                    new_feature[field.name()] = census_feature[field.name()]
                
                # Recalculate demographic attributes based on area ratio
                for field in fields_to_recalculate:
                    recalculated_value = census_feature[field] * area_ratio
                    new_feature[field + new_field_suffix] = recalculated_value
                
                # Add the new feature to the new layer
                new_layer_data_provider.addFeature(new_feature)

# Add the new layer to the project
QgsProject.instance().addMapLayer(new_layer)

# Save the new layer to a file (e.g., GeoPackage)
output_file = "path_to_output_file.gpkg"  # Replace with your desired file path
QgsVectorFileWriter.writeAsVectorFormat(
    new_layer,
    output_file,
    "UTF-8",
    new_layer.crs(),
    "GPKG"
)

# Optional: Aggregate recalculated data for each circle
for circle_feature in circles_layer.getFeatures():
    circle_geom = circle_feature.geometry()
    location_name = circle_feature['LocationNa']
    location_id = circle_feature['LocationID']
    aggregate_dict = {field: 0 for field in fields_to_recalculate}
    
    for new_feature in new_layer.getFeatures():
        new_geom = new_feature.geometry()
        
        if new_geom.intersects(circle_geom):
            for field in fields_to_recalculate:
                aggregate_dict[field] += new_feature[field + new_field_suffix]
    
    # Print or store the aggregated results for this circle
    print(f"Location: {location_name} (ID: {location_id}):")
    for field, aggregate_value in aggregate_dict.items():
        # Format as integer with commas
        formatted_value = f"{int(round(aggregate_value)):,}"
        print(f"  {field}: {formatted_value}")
