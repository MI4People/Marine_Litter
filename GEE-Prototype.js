var selectedRegion;
var position;


// TO-DO add var for zoom coordinates and timepoints where litter is visible
var regionArray = {
  'Durban': {
    'timepoints':['2019-04-19','2019-04-24','2019-04-29'], 
    'imageName':[durban190419, durban190425, durban190429],
    'story': 'Flood event on 22nd and 23rd of April 2019 in this region.',
    'pickDate': ['2019-04-24'],
    'pickPosition': [31.078424502408225, -29.855263513511353]
  },
  'Baltic sea': {
    'timepoints':['2019-06-09','2019-06-10', '2019-06-26', '2019-06-29', '2020-07-13'],
    'imageName':[image2, image3, image4, image5, image6],
    'story': '',
    'pickDate': ['2019-06-10'],
    'pickPosition': [11.835695130768501, 54.2792381124053]
  }
};

// Title
var title = ui.Label({
  value: 'Marine Litter',
  style: {
    fontSize: '24px',
    fontWeight: 'bold',
    color: '#00796b', // Dunkelgrün
    margin: '0 0 4px 0',
    padding: '10px',
  }
});

// General description 
var description = ui.Label({
  value: 'This prototype leverages artificial intelligence (AI) to identify marine litter across various geographic regions. The used AI is based on research published in "Identifying Marine Litter with Deep Learning Techniques" (https://doi.org/10.1016/j.isci.2023.108402) and implemented with code from GitHub. Developed by MI4People, the tool aims to facilitate the monitoring and management of marine environments by providing an intuitive interface for the visualization of litter distribution. Users can explore different regions and time points to assess changes and trends. Additionally, the "Layers" function, located at the top right corner of the map, allows users to toggle the visibility of individual map layers for a customized viewing experience. Predicted marine litter is highlighted in red.',
  style: {
    fontSize: '15px',
    margin: '0 0 15px 0',
    padding: '10px',
  }
});

// Titel for region selector
var dropTitle = ui.Label({
  value: 'Select a specific region',
  style: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#004D40', // Dunkleres Grün
    margin: '10px 0 5px 0',
    padding: '5px',
  }
});

// Region selector
var dropdown = ui.Select({
  items: Object.keys(regionArray),
  placeholder: 'Select region',
  style: {
    margin: '5px 0 20px 0'
  },
  onChange: function(region) {
    selectedRegion = region;
    var details = regionArray[region];
    timepoint.items().reset(details.timepoints);
    storyText.setValue(details.story);
    position = details.pickPosition;
    if (details.timepoints.length > 0) {
      timepoint.setValue(details.pickDate[0], /* fireEvent */ true); //[details.timepoints.length - 1], /* fireEvent */ true);
    }
  }
});

// General description 
var storyText = ui.Label({
  value: 'Story behind the region.',
  style: {
    fontSize: '15px',
    margin: '0 0 15px 0',
    padding: '10px',
  }
});

// Titel for date selector
var timeTitle = ui.Label({
  value: 'Select a specific date',
  style: {
    fontSize: '18px',
    fontWeight: 'bold',
    color: '#004D40', // Dunkleres Grün
    margin: '10px 0 5px 0',
    padding: '5px',
  }
});

// Time selector
var timepoint = ui.Select({
  placeholder: 'Select timepoint',
  style: {
    margin: '5px 0 20px 0'
  },
  onChange: function(selectedTime) {
    var days = getAdjacentDates(selectedTime);
    var startTime = days.startTime;
    var endTime = days.endTime;
    var timepointIndex = regionArray[selectedRegion].timepoints.indexOf(selectedTime);
    var maskLayer = regionArray[selectedRegion].imageName[timepointIndex];
    showImage(maskLayer, startTime, endTime, position);
    position == 0;
  }
});


// Disclaimer
var disclaimer = ui.Label({
  value: 'The information and functionalities provided by this tool are for informational purposes only. MI4People makes no warranties regarding the accuracy or reliability of the data or visualizations. Use of this tool is at the user’s own risk. MI4People is not liable for any damages arising from its use. Users are responsible for adhering to copyright and license terms of the underlying model and code.',
  style: {
    fontSize: '12px',
    margin: '60px 0 15px 0',
    padding: '10px',
  }
});



//Sidebar
var sidebar = ui.Panel ({
  layout: ui.Panel.Layout.flow('vertical'),
  widgets: [title, description, dropTitle, dropdown, storyText, timeTitle, timepoint, disclaimer],
  style: {
    width: '350px',
    padding: '8px',
  }
});

var map = ui.Map();

ui.root.clear();
ui.root.add(sidebar);
ui.root.add(map);

// init show
dropdown.setValue(Object.keys(regionArray)[0], true); 


function showImage(maskLayer, startTime, endTime, position) {
  map.layers().reset();
  
  var frame = maskLayer.geometry();
  var aoi = ee.Geometry.Polygon(frame.coordinates());
  
  var dataset = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi)
  .filterDate(startTime, endTime)
  .select(['B4', 'B3', 'B2']);
  
  var meanImage = dataset.mean();
  var rescale = meanImage.divide(10000);
  var clipImage = rescale.clip(aoi);

  var visParam = {bands: ["B4", "B3", "B2"], min: 0, max: 0.4};
  map.addLayer(clipImage, visParam, "Sentinel-2-Image");

  var mask = maskLayer.gt(100); 
  var maskedImage = maskLayer.updateMask(mask);
  map.addLayer(maskedImage, {min: 0, max: 237, palette: ['green', 'red']}, 'Marine Litter');

  if (position === 0) {
    map.centerObject(maskLayer, 12);
  } else {
    map.centerObject(ee.Geometry.Point(position), 14);
  }
}

function getAdjacentDates(inputDate) {
  var date = new Date(inputDate);
  
  var dateBefore = new Date(date);
  dateBefore.setDate(date.getDate() - 1);
  var dateBeforeString = dateBefore.toISOString().split('T')[0];
  
  var dateAfter = new Date(date);
  dateAfter.setDate(date.getDate() + 1);
  var dateAfterString = dateAfter.toISOString().split('T')[0];
  
  return {
    startTime: dateBeforeString,
    endTime: dateAfterString
  };
}
