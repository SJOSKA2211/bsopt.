import ray

from src.mlops.ray_runner import RayExperimentRunner

RayExperimentRunner._connection_failed = False
if ray.is_initialized(): ray.shutdown()
runner = RayExperimentRunner(ray_address="invalid://address:9999", mlflow_tracking_uri="")
runner.connect()
print("FAILED:", RayExperimentRunner._connection_failed)
