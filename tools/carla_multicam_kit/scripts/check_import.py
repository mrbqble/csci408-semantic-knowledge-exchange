import sys
import carla, numpy, PIL
print("python", sys.version.split()[0])
print("carla client", carla.Client("localhost", 2000).get_client_version())
print("carla module", carla.__file__)
print("numpy", numpy.__version__, "| pillow", PIL.__version__)
