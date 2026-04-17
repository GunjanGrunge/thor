import torch
import sys

print(f"Python: {sys.version}")
print(f"Torch: {torch.__version__}")
try:
    available = torch.cuda.is_available()
    print(f"CUDA Available: {available}")
    if available:
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Version: {torch.version.cuda}")
except Exception as e:
    print(f"Error checking CUDA: {e}")
