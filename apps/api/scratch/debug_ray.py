import ray
import os

tmp_dir = "/home/kamau/bsopt./apps/api/tmp/ray"
os.makedirs(tmp_dir, exist_ok=True)

try:
    print("Starting ray...")
    ray.init(num_cpus=1, include_dashboard=False, _temp_dir=tmp_dir)
    print("Ray started!")
    print(ray.cluster_resources())
    
    @ray.remote
    def f(x):
        return x * x
    
    print("Running task...")
    res = ray.get(f.remote(10))
    print(f"Result: {res}")
    
finally:
    ray.shutdown()
    print("Ray shutdown.")
