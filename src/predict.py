# load model
# - pip install marinedebrisdetector
# packages import
import torch
from marinedebrisdetector.predictor import ScenePredictor

def predict(image_path):
    model = torch.hub.load("marccoru/marinedebrisdetector", "unetpp")
    prediction_path = image_path.replace(".tif", "_prediction.tif")
    predictor = ScenePredictor()
    predictor.predict(model, image_path, prediction_path)
    return prediction_path

image_path = "durban_20190424.tif"
prediction = predict(image_path)