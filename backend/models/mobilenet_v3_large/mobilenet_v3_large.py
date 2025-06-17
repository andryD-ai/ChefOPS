import torch
import torchvision.models as models
import torch.nn as nn
from torchvision import transforms
from dataclasses import dataclass
import cv2
from PIL import Image

@dataclass
class MobilenetV3Config():
  clss:int = 6
  device:str = 'cpu'
  img_size:int = 224

class MobilenetV3Large():
    def __init__(self, config):
        self.config = config
        self.clss = config.clss
        self.device = 'cpu'  if config.device == None else config.device
        self.img_size = 224 if config.img_size == None else config.img_size

        # Load MobileNetV3-Large pretrained on ImageNet
        self.mobilenet_v3_large = models.mobilenet_v3_large(pretrained=True)

        # Modify the final layer for a custom number of classes (here 6)
        self.mobilenet_v3_large.classifier[3] = nn.Linear(in_features=1280, out_features=self.clss)

         # Define data transformations
        self.transform = transforms.Compose([
            transforms.Resize((self.img_size,self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

    def classification(self, img):
        '''
        Classification single image
        '''

         # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
        # Convert to PIL Image
        img = Image.fromarray(img)
       
        # Apply the transform
        input_tensor = self.transform(img).unsqueeze(0)

        with torch.no_grad():
            outputs = self.mobilenet_v3_large(input_tensor.to(self.device))
            _, predicted = torch.max(outputs.data, 1)
            return predicted

    @classmethod
    def from_pretrained(cls, model_path, device):
        # Load model from checkpoint
        checkpoint = torch.load(model_path, map_location=device)

        # Restore model and optimizer states
        # Strip the '_orig_mod.' prefix
        new_state_dict = {}
        for k, v in checkpoint['model_state_dict'].items():
            new_key = k.replace("_orig_mod.", "")  # Remove prefix
            new_state_dict[new_key] = v

        config_args = dict(clss = 6, device=device, img_size = 224)
        config = MobilenetV3Config(**config_args)

        model = MobilenetV3Large(config)

        model.mobilenet_v3_large.to(model.device)
        model.mobilenet_v3_large.load_state_dict(new_state_dict)
        model.mobilenet_v3_large.eval()
        
        return model