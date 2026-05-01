
import ray

try:
    ray.init(address="ray://127.0.0.1:10001")
    print("Ray connected successfully")
    @ray.remote
    def f() -> int:
        return 1
    print(ray.get(f.remote()))
    ray.shutdown()
except Exception as e:
    print(f"Ray connection failed: {e}")
