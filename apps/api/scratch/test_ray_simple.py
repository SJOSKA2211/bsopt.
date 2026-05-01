import ray

try:
    ray.init()
    print("Ray init successful")
    @ray.remote
    def f(x): return x * x
    print(f"Ray task: {ray.get(f.remote(2))}")
except Exception as e:
    print(f"Ray init failed: {e}")
finally:
    ray.shutdown()
