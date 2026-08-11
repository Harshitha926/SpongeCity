// ============================================
// SPONGE CITY RISK DETECTOR — GRID DATA EXPORT
// Area: HSR Layout / Bellandur, Bengaluru
// Run this in the Google Earth Engine Code Editor:
// https://code.earthengine.google.com/
// ============================================

var aoi = ee.Geometry.Rectangle([77.63, 12.91, 77.68, 12.93]);
Map.centerObject(aoi, 13);

// ============================================
// STEP 1: CREATE GRID (~100m cells)
// ============================================

var cellSize = 0.0009; // ~100m at this latitude
var xmin = 77.63, xmax = 77.68, ymin = 12.91, ymax = 12.93;

var xSteps = ee.List.sequence(xmin, xmax, cellSize);
var ySteps = ee.List.sequence(ymin, ymax, cellSize);

var grid = ee.FeatureCollection(
  xSteps.map(function(x) {
    return ySteps.map(function(y) {
      var x0 = ee.Number(x);
      var y0 = ee.Number(y);
      var rect = ee.Geometry.Rectangle([x0, y0, x0.add(cellSize), y0.add(cellSize)]);
      return ee.Feature(rect);
    });
  }).flatten()
);

print('Number of grid cells:', grid.size());
Map.addLayer(grid, {}, 'Grid', false);

// ============================================
// STEP 2: FEATURE — ELEVATION (SRTM DEM)
// ============================================

var elevation = ee.Image('USGS/SRTMGL1_003').select('elevation').rename('elevation');

// ============================================
// STEP 3: FEATURE — IMPERVIOUSNESS (built-up %)
// ESA WorldCover class 50 = Built-up
// ============================================

var worldcover = ee.Image('ESA/WorldCover/v100/2020').select('Map');
var impervious = worldcover.eq(50).rename('impervious');

// ============================================
// STEP 4: FEATURE — DISTANCE TO PERMANENT WATER/DRAINS
// JRC Global Surface Water as proxy for waterbodies
// ============================================

var gsw = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence');
var permanentWater = gsw.gt(50);
var distanceToWater = permanentWater.fastDistanceTransform(256).sqrt()
  .multiply(ee.Image.pixelArea().sqrt())
  .rename('dist_to_water');

// Preserve missing radar coverage as -1 instead of treating it as a dry pixel.
// A flat VH < -18 dB threshold can also fire on flat rooftops, smooth roads,
// and radar shadow, not just water. A future version should compare against a
// pre-flood baseline (relative VH drop) instead of using an absolute threshold.
function buildFloodLabel(collection, bandName, threshold) {
  var hasImages = collection.size().gt(0);
  var imageWithData = ee.Image(ee.Algorithms.If(
    hasImages,
    collection.select(bandName).median(),
    ee.Image.constant(-1).rename(bandName)
  ));
  var pixelHasData = ee.Image(ee.Algorithms.If(
    hasImages,
    imageWithData.mask().gt(0),
    ee.Image.constant(0)
  )).rename(bandName + '_has_data');
  var labelWithData = imageWithData.lt(threshold)
    .where(pixelHasData.not(), -1)
    .rename(bandName);

  return labelWithData.addBands(pixelHasData);
}

// ============================================
// STEP 5: LABEL — FLOOD EVENT 1 (May 22, 2026, radar)
// Confirmed real flood event, Bellandur/Silk Board/ORR
// ============================================

var s1Flood1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(aoi)
  .filterDate('2026-05-22', '2026-05-27')
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'));

print('Flood event 1 image count:', s1Flood1.size());
var floodEvent1 = buildFloodLabel(s1Flood1, 'VH', -18)
  .rename(['flood_event1', 'flood_event1_has_data']);

// ============================================
// STEP 6: LABEL — FLOOD EVENT 2 (secondary window, ~June 2026)
// ============================================

var s1Flood2 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(aoi)
  .filterDate('2026-05-27', '2026-06-06')
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'));

print('Flood event 2 image count:', s1Flood2.size());
var floodEvent2 = buildFloodLabel(s1Flood2, 'VH', -18)
  .rename(['flood_event2', 'flood_event2_has_data']);

// ============================================
// STEP 7: COMBINE + REDUCE TO GRID
// ============================================

var combinedImage = elevation
  .addBands(impervious)
  .addBands(distanceToWater)
  .addBands(floodEvent1)
  .addBands(floodEvent2);

var gridWithData = combinedImage.reduceRegions({
  collection: grid,
  reducer: ee.Reducer.mean(),
  scale: 30
});

print('Sample of grid data:', gridWithData.limit(5));

Export.table.toDrive({
  collection: gridWithData,
  description: 'sponge_city_grid_dataset',
  fileFormat: 'CSV'
});

// ============================================
// DRY-SEASON CONTROL (run separately, or uncomment)
// Pulls radar for Jan 2026 (no rain) to catch false positives
// ============================================

var s1Dry = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(aoi)
  .filterDate('2026-01-01', '2026-01-31')
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'));

print('Dry-season image count:', s1Dry.size());
var dryWaterMask = buildFloodLabel(s1Dry, 'VH', -18)
  .rename(['dry_season_water', 'dry_season_water_has_data']);

var gridWithDryData = dryWaterMask.reduceRegions({
  collection: grid,
  reducer: ee.Reducer.mean(),
  scale: 30
});

Export.table.toDrive({
  collection: gridWithDryData,
  description: 'sponge_city_dry_season_control',
  fileFormat: 'CSV'
});

print('Two export tasks created — go to the Tasks tab and click RUN on each');
